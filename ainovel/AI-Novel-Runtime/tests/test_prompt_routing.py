from runtime.execution.agent import ChapterDraftAgent
from runtime.execution.model import DeterministicModel
from runtime.prompt.routing import route_generation


class _DummyModel(DeterministicModel):
    def __init__(self, model_id: str, provider: str):
        self.model_id = model_id
        self.provider = provider


PACKAGE = {
    "task": {
        "task_id": "TASK-1",
        "goal": "write chapter",
        "capability": "ChapterDraft",
        "model_id": "gpt-5.4",
    },
    "content_hash": "sha256:" + "a" * 64,
    "provenance": {"derived_from": ["CHR-00001@v1"], "source_version": 1},
    "context": {"characters": [{"id": "CHR-00001", "name": "主角"}]},
}

EXTRA_VARS = {
    "story_state": "story so far",
    "narrative_mandate": "why now",
    "chapter_ir": "ir",
    "scene_plan": "scene plan",
    "character_runtime": "character runtime",
    "chapter_objective": "objective",
    "director_brief": "brief",
    "speech_profiles": "speech profiles",
    "recent_openings": "recent openings",
    "long_arc": "long arc",
    "approved_state": "approved state",
    "approved_state_constraints": ["fact must be consumed"],
}


def test_route_generation_prefers_model_specific_pack_for_gpt():
    route = route_generation(model_id="gpt-5.4", provider="openai", task_type="ChapterDraft")
    assert route.prompt_version == "13.0.0"
    assert route.constraint_pack_id == "gpt-v13"
    assert "matched profile gpt-5.4" in route.rationale
    assert "constraint_pack=gpt-v13" in route.rationale


def test_route_generation_prefers_model_specific_pack_for_deepseek():
    route = route_generation(
        model_id="deepseek-chat", provider="deepseek", task_type="ChapterDraft"
    )
    assert route.prompt_version == "13.0.0"
    assert route.constraint_pack_id == "deepseek-v13"
    assert "matched profile deepseek-chat" in route.rationale
    assert "constraint_pack=deepseek-v13" in route.rationale


def test_route_generation_uses_failure_mode_to_override_pack():
    route = route_generation(
        model_id="gpt-5.4",
        provider="openai",
        task_type="ChapterDraft",
        known_failure_mode="AI-tell and dash-aside leakage",
    )
    assert route.constraint_pack_id == "deepseek-v13"
    assert route.metadata["constraint_directives"]
    assert any("dash-aside" in directive or "meta-reference" in directive
               for directive in route.metadata["constraint_directives"])


def test_agent_captures_route_and_profile_from_model_id():
    agent = ChapterDraftAgent(model=_DummyModel("gpt-5.4", "openai"))
    agent.run(PACKAGE, variables=EXTRA_VARS)

    assert agent.last_route is not None
    assert agent.last_route.prompt_version == "13.0.0"
    assert agent.last_route.constraint_pack_id == "gpt-v13"
    assert agent.model_profile["model_id"] == "gpt-5.4"
    assert agent.model_profile["provider"] == "openai"
    assert agent.constraint_pack["constraint_pack_id"] == "gpt-v13"
    # rendered_text lives on the RenderedPrompt, not the PromptManifest: the
    # manifest is provenance (hashes) and prompt-manifest.schema.json is
    # additionalProperties:false with no rendered_text slot (ADR-007).
    #
    # The route reaches the prompt as a STRUCTURED note (the v13
    # {model_profile_note} slot), not as route.rationale's prose. Asserting the
    # rationale wording here encoded a contract the agent never promised.
    rendered = agent.last_rendered_prompt.rendered_text
    assert "model=gpt-5.4" in rendered
    assert "provider=openai" in rendered
    assert "pack=gpt-v13" in rendered
    # The rationale wording stays available on the route object itself.
    assert "matched profile gpt-5.4" in agent.last_route.rationale
    assert "constraint_pack=gpt-v13" in agent.last_route.rationale
    assert agent.last_prompt_manifest.route_summary["constraint_pack_id"] == "gpt-v13"


def test_agent_routes_stably_for_same_input():
    agent = ChapterDraftAgent(model=_DummyModel("deepseek-chat", "deepseek"))
    agent.run(PACKAGE, variables=EXTRA_VARS)
    first_route = agent.last_route
    first_profile = dict(agent.model_profile)
    first_pack = dict(agent.constraint_pack)

    agent.run(PACKAGE, variables=EXTRA_VARS)

    assert agent.last_route == first_route
    assert agent.model_profile == first_profile
    assert agent.constraint_pack == first_pack


def test_approved_state_constraints_enter_rendered_prompt():
    """The REAL delivery path for approved-state constraints.

    `director/plan.py` folds approved_state_constraints into
    objective["constraints"] (line ~123), and the objective reaches the drafter
    through the DECLARED `chapter_objective` variable. No chapter-draft template
    declares or references a standalone `{approved_state_constraints}` slot, so
    binding that variable alone renders nothing — the previous version of this
    test asserted a path the templates never consumed.
    """
    agent = ChapterDraftAgent(model=_DummyModel("gpt-5.4", "openai"))
    variables = dict(EXTRA_VARS)
    variables["chapter_objective"] = "objective\n约束：fact must be consumed"
    agent.run(PACKAGE, variables=variables)

    assert "fact must be consumed" in agent.last_rendered_prompt.rendered_text
    assert agent.last_prompt_manifest.route_summary["model_id"] == "gpt-5.4"


def test_standalone_constraints_variable_is_not_consumed_by_any_template():
    """Guard the finding above: binding approved_state_constraints WITHOUT
    folding it into the objective puts nothing in the prompt. If a future
    template adds a real slot for it, this test should be updated deliberately
    rather than the constraint silently starting/stopping to flow."""
    agent = ChapterDraftAgent(model=_DummyModel("gpt-5.4", "openai"))
    agent.run(PACKAGE, variables=EXTRA_VARS)

    assert EXTRA_VARS["approved_state_constraints"] == ["fact must be consumed"]
    assert "fact must be consumed" not in agent.last_rendered_prompt.rendered_text
