import uuid
import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import User, Classroom, ClassroomMember, Assignment, Submission
from ..schemas import (
    ClassroomCreate,
    ClassroomResponse,
    AssignmentCreate,
    AssignmentResponse,
    SubmissionCreate,
    SubmissionResponse,
)
from ..auth import get_current_user, require_role

router = APIRouter(prefix="/classrooms", tags=["Classrooms"])


@router.post("", response_model=ClassroomResponse)
async def create_classroom(
    req: ClassroomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("instructor", "org_admin")),
):
    """Creates a new classroom (Instructor only)."""
    join_code = str(uuid.uuid4())[:8].upper()
    classroom = Classroom(
        instructor_id=current_user.id,
        organization_id=current_user.organization_id,
        name=req.name,
        description=req.description,
        join_code=join_code,
    )
    db.add(classroom)
    await db.commit()
    await db.refresh(classroom)
    return classroom


@router.get("", response_model=List[ClassroomResponse])
async def list_my_classrooms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists classrooms where the user is instructor or enrolled student."""
    if current_user.role in ("instructor", "org_admin", "platform_admin"):
        result = await db.execute(select(Classroom).where(Classroom.instructor_id == current_user.id))
        return result.scalars().all()
    else:
        # Enrolled classrooms
        result = await db.execute(
            select(Classroom)
            .join(ClassroomMember, Classroom.id == ClassroomMember.classroom_id)
            .where(ClassroomMember.user_id == current_user.id)
        )
        return result.scalars().all()


@router.post("/join/{join_code}")
async def join_classroom(
    join_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enrolls student into a classroom using a valid join code."""
    result = await db.execute(select(Classroom).where(Classroom.join_code == join_code))
    classroom = result.scalar_one_or_none()
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid classroom join code")

    existing = await db.execute(
        select(ClassroomMember).where(
            ClassroomMember.classroom_id == classroom.id,
            ClassroomMember.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_enrolled", "classroom_id": classroom.id}

    membership = ClassroomMember(classroom_id=classroom.id, user_id=current_user.id, role="student")
    db.add(membership)
    await db.commit()
    return {"status": "enrolled", "classroom_id": classroom.id, "classroom_name": classroom.name}


@router.post("/assignments", response_model=AssignmentResponse)
async def create_assignment(
    req: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("instructor", "org_admin")),
):
    """Publishes a new coding exercise/assignment to a classroom."""
    result = await db.execute(
        select(Classroom).where(Classroom.id == req.classroom_id, Classroom.instructor_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign to classroom you do not own")

    assignment = Assignment(
        classroom_id=req.classroom_id,
        title=req.title,
        description=req.description,
        template_notebook_json=json.dumps(req.template_notebook),
        due_date=req.due_date,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


@router.get("/{classroom_id}/assignments", response_model=List[AssignmentResponse])
async def list_assignments(
    classroom_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists assignments for an authorized classroom."""
    result = await db.execute(select(Assignment).where(Assignment.classroom_id == classroom_id))
    return result.scalars().all()


@router.post("/submissions", response_model=SubmissionResponse)
async def submit_assignment(
    req: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submits an immutable snapshot of student's notebook work for grading."""
    submission = Submission(
        assignment_id=req.assignment_id,
        student_id=current_user.id,
        notebook_json=json.dumps(req.notebook_content),
        status="submitted",
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission


@router.get("/assignments/{assignment_id}/submissions", response_model=List[SubmissionResponse])
async def list_assignment_submissions(
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("instructor", "org_admin")),
):
    """Instructor view: lists student submissions for an assignment."""
    result = await db.execute(select(Submission).where(Submission.assignment_id == assignment_id))
    return result.scalars().all()


@router.put("/submissions/{submission_id}/review")
async def review_submission(
    submission_id: str,
    grade: float,
    feedback: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("instructor", "org_admin")),
):
    """Instructor review: grades submission and provides written feedback."""
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    submission.grade = grade
    submission.feedback = feedback
    submission.status = "reviewed"
    await db.commit()
    return {"status": "ok", "grade": grade, "submission_id": submission_id}

