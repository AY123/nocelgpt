"""Historical candidate audit bundle, never a freshness or acceptance permit."""

from dataclasses import dataclass

from anovel.context.models import ContextArtifact, ContextError, FrozenContextInputs
from anovel.context.scene import CandidateSceneProjection


@dataclass(frozen=True, slots=True)
class SceneProjection:
    candidate: CandidateSceneProjection
    inputs: FrozenContextInputs
    context: ContextArtifact

    def __post_init__(self) -> None:
        if (
            type(self.candidate) is not CandidateSceneProjection
            or type(self.inputs) is not FrozenContextInputs
            or type(self.context) is not ContextArtifact
            or self.inputs.candidate != self.candidate
            or self.context.input_hash != self.inputs.content_hash
            or self.context.request_hash != self.inputs.request.content_hash
        ):
            raise ContextError("invalid scene projection bundle")

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "workflow_scene_projection",
            "schema_version": "1.0",
            "visibility": "AUDIT_ONLY",
            "candidate": self.candidate.to_dict(),
            "inputs": self.inputs.to_dict(),
            "context": self.context.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> "SceneProjection":
        if (
            type(value) is not dict
            or set(value)
            != {
                "record_type",
                "schema_version",
                "visibility",
                "candidate",
                "inputs",
                "context",
            }
            or (value["record_type"], value["schema_version"], value["visibility"])
            != ("workflow_scene_projection", "1.0", "AUDIT_ONLY")
        ):
            raise ContextError("invalid scene projection record")
        return cls(
            CandidateSceneProjection.from_dict(value["candidate"]),
            FrozenContextInputs.from_dict(value["inputs"]),
            ContextArtifact.from_dict(value["context"]),
        )
