import uuid
from sqlalchemy import Boolean, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column, validates
from app.models.base import Base
from app.utils.db import GUID
from shared.db.audit_mixin import AuditMixin


class CustomerModel(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    country: Mapped[str] = mapped_column(String, nullable=False)
    is_ngo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_donor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    currency = mapped_column(String, nullable=False)
    users = relationship("UserModel", back_populates="customer")


class DonorGranteeModel(Base, AuditMixin):
    __tablename__ = "donor_grantees"

    __table_args__ = (
        UniqueConstraint("donor_id", "grantee_id", name="uq_donor_grantees_donor_id_grantee_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        index=True,
        default=lambda: uuid.uuid4(),
    )
    donor_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("customers.id"), index=True)

    grantee_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("customers.id"), index=True)

    donor = relationship("CustomerModel", foreign_keys=[donor_id])
    grantee = relationship("CustomerModel", foreign_keys=[grantee_id])

    @validates("donor")
    def validate_donor(self, key, donor):
        if not donor.is_donor:
            raise ValueError("Customer has to be a donor")
        return donor

    @validates("grantee")
    def validate_grantee(self, key, grantee):
        if not grantee.is_ngo:
            raise ValueError("Customer has to be a grantee")
        return grantee
