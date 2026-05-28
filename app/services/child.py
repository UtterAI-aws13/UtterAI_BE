"""Service-layer logic for child-profile CRUD."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import ChildStatus, UserRole
from app.models.entities import Child
from app.repositories.child import ChildRepository
from app.schemas.auth import UserRead
from app.schemas.child import ChildCreateRequest, ChildRead, ChildUpdateRequest


class ChildService:
    """Apply ownership and role rules around child-profile operations."""

    def __init__(self, db: Session) -> None:
        self.repository = ChildRepository(db)

    def create(self, request: ChildCreateRequest, current_user: UserRead) -> ChildRead:
        """Create a child owned by the current therapist or chosen by an admin.

        Therapists always create children under their own account. Admins may
        pass `therapist_id` explicitly so they can register data on behalf of a
        therapist without weakening ownership rules elsewhere.
        """

        therapist_id = current_user.id
        if current_user.role == UserRole.ADMIN:
            therapist_id = request.therapist_id or current_user.id
        elif current_user.role != UserRole.THERAPIST:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only therapists or admins can create child profiles.",
            )

        child = Child(
            therapist_id=therapist_id,
            name=request.name,
            birth_date=request.birth_date,
            gender=request.gender,
            memo=request.memo,
            status=ChildStatus.ACTIVE,
        )
        return ChildRead.model_validate(self.repository.create(child))

    def list(self, current_user: UserRead) -> list[ChildRead]:
        """List children according to role-based visibility."""

        if current_user.role == UserRole.ADMIN:
            children = self.repository.list_active()
        elif current_user.role == UserRole.THERAPIST:
            children = self.repository.list_active(therapist_id=current_user.id)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only therapists or admins can view child profiles.",
            )
        return [ChildRead.model_validate(child) for child in children]

    def get(self, child_id: uuid.UUID, current_user: UserRead) -> ChildRead:
        """Return one child after enforcing ownership checks."""

        child = self._get_accessible_child(child_id, current_user)
        return ChildRead.model_validate(child)

    def update(
        self,
        child_id: uuid.UUID,
        request: ChildUpdateRequest,
        current_user: UserRead,
    ) -> ChildRead:
        """Update editable child fields while preserving owner linkage."""

        child = self._get_accessible_child(child_id, current_user)
        update_data = request.model_dump(exclude_unset=True)
        for field_name, value in update_data.items():
            setattr(child, field_name, value)
        return ChildRead.model_validate(self.repository.update(child))

    def delete(self, child_id: uuid.UUID, current_user: UserRead) -> ChildRead:
        """Soft-delete a child profile by flipping its lifecycle status."""

        child = self._get_accessible_child(child_id, current_user)
        child.status = ChildStatus.DELETED
        return ChildRead.model_validate(self.repository.update(child))

    def _get_accessible_child(self, child_id: uuid.UUID, current_user: UserRead) -> Child:
        """Load a child and enforce therapist ownership or admin override."""

        child = self.repository.get_by_id(child_id)
        if child is None or child.status == ChildStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Child profile not found.",
            )

        if current_user.role == UserRole.ADMIN:
            return child

        if current_user.role == UserRole.THERAPIST and child.therapist_id == current_user.id:
            return child

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this child profile.",
        )
