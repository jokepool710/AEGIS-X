from dataclasses import asdict, dataclass
from enum import Enum

from aegis.investigation.evidence import EvidenceBundle


class ClaimType(str, Enum):
    OBSERVATION = "observation"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"


@dataclass(frozen=True)
class InvestigativeClaim:
    claim_id: str
    text: str
    claim_type: ClaimType
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class CitationValidation:
    claim_id: str
    valid: bool
    resolved_evidence_ids: tuple[str, ...]
    invalid_evidence_ids: tuple[str, ...]
    reason: str | None = None


@dataclass(frozen=True)
class GroundedClaim:
    claim: InvestigativeClaim
    citations: CitationValidation

    def to_dict(self) -> dict[str, object]:
        return {
            "claim": {**asdict(self.claim), "claim_type": self.claim.claim_type.value},
            "citations": asdict(self.citations),
        }


class CitationValidationError(ValueError):
    pass


class EvidenceCitationValidator:
    """Validate that investigative claims cite evidence from the active incident bundle."""

    def validate(self, claim: InvestigativeClaim, bundle: EvidenceBundle) -> CitationValidation:
        if not claim.claim_id.strip():
            return CitationValidation(claim.claim_id, False, (), (), "claim_id is required")
        if not claim.text.strip():
            return CitationValidation(claim.claim_id, False, (), (), "claim text is required")
        if not claim.evidence_ids:
            return CitationValidation(claim.claim_id, False, (), (), "claim has no evidence citations")

        available = bundle.evidence_ids
        resolved = tuple(evidence_id for evidence_id in claim.evidence_ids if evidence_id in available)
        invalid = tuple(evidence_id for evidence_id in claim.evidence_ids if evidence_id not in available)
        if invalid:
            return CitationValidation(
                claim.claim_id, False, resolved, invalid,
                "claim cites evidence outside the active incident bundle",
            )
        return CitationValidation(claim.claim_id, True, resolved, ())

    def ground(self, claim: InvestigativeClaim, bundle: EvidenceBundle) -> GroundedClaim:
        validation = self.validate(claim, bundle)
        if not validation.valid:
            raise CitationValidationError(validation.reason or "invalid evidence citations")
        return GroundedClaim(claim, validation)

    def ground_many(self, claims: tuple[InvestigativeClaim, ...] | list[InvestigativeClaim],
                    bundle: EvidenceBundle) -> tuple[GroundedClaim, ...]:
        seen_claim_ids: set[str] = set()
        grounded = []
        for claim in claims:
            if claim.claim_id in seen_claim_ids:
                raise CitationValidationError(f"duplicate claim_id: {claim.claim_id}")
            seen_claim_ids.add(claim.claim_id)
            grounded.append(self.ground(claim, bundle))
        return tuple(grounded)
