"""Serial production subdomain (ANES v2, roadmap P14+P15 consumer, P17 seed).

The first real consumer of the full production chain: runs many chapters in
sequence and carries state (as a fold cursor, ADR-008) between them, proving P14
(StoryState fold) and P15 (Novel Brain) connect end-to-end. Never gates the
serial (ADR-003); reads only, never writes facts (ADR-006).
"""

from .loop import (ChapterSpec, ChapterRun, SerialResult,
                   plan_chapters, plan_continuation_from_rolling_plan, run_serial)
from .run_manifest import (build_run_manifest, write_run_manifest,
                           next_run_id)
from .live_baseline_report import (build_live_baseline_report,
                                   write_live_baseline_report,
                                   next_report_id)
from .live_baseline_precheck import (build_precheck_environment,
                                     build_precheck_report,
                                     PRECHECK_BASELINE_ID)
from .live_baseline_run import (LiveBaselineRunConfig,
                                build_live_baseline_config,
                                BASELINE_5CH_ID,
                                BASELINE_3CH_ID,
                                BASELINE_5CH_CHAPTERS,
                                BASELINE_3CH_CHAPTERS,
                                BASELINE_5CH_BUDGET_CNY,
                                BASELINE_3CH_BUDGET_CNY,
                                BASELINE_5CH_PROMPT_VERSION,
                                BASELINE_5CH_MODEL_PROVIDER,
                                BASELINE_5CH_MODEL_ID)
from .baseline_freeze import (build_baseline_freeze_record,
                              write_baseline_freeze_record,
                              list_baseline_freeze_refs,
                              load_baseline_freeze_record,
                              FREEZE_KIND,
                              FREEZE_VERSION)
from .baseline_comparison import (compare_baseline_freeze_records,
                                  compare_baseline_freeze_paths,
                                  COMPARISON_KIND,
                                  COMPARISON_VERSION)
from .baseline_compare_report import (build_baseline_compare_report,
                                      write_baseline_compare_report,
                                      compare_and_write_baseline_report,
                                      CATEGORY as BASELINE_COMPARE_REPORT_CATEGORY,
                                      REPORT_VERSION as BASELINE_COMPARE_REPORT_VERSION,
                                      REPORT_KIND as BASELINE_COMPARE_REPORT_KIND)
from .quality_snapshot import (build_quality_snapshot,
                               compare_quality_snapshots,
                               QUALITY_SNAPSHOT_KIND,
                               QUALITY_SNAPSHOT_VERSION)
from .validation_report import (build_short_run_validation_report,
                                build_short_run_validation_report_from_bodies,
                                VALIDATION_REPORT_KIND,
                                VALIDATION_REPORT_VERSION)
from .validation_artifacts import write_short_run_validation_report, CATEGORY as SHORT_RUN_VALIDATION_CATEGORY
from .validation_query import (list_short_run_validation_reports,
                               load_short_run_validation_report)
from .body_pair_report import (build_body_pair_validation_report,
                               BODY_PAIR_REPORT_KIND,
                               BODY_PAIR_REPORT_VERSION)
from .speech_profile import SpeechProfile, build_speech_profile, render_speech_profiles, merge_speech_profiles, coerce_speech_profile
from .launch_30ch_summary_query import (list_30ch_launch_summaries,
                                         load_30ch_launch_summary)
from .launch_30ch_summary_artifacts import write_30ch_launch_summary
from .run_aggregate_query import (list_run_aggregates,
                                  load_run_aggregate)
from .run_aggregate_artifacts import write_run_aggregate
from .checkpoints import (load_serial_checkpoint, load_serial_checkpoints,
                          backfill_checkpoints, build_checkpoint,
                          CHECKPOINT_INDICES)
from .rolling_plan import (build_rolling_plan, load_rolling_plan,
                           load_rolling_plans, ROLLING_PLAN_CATEGORY)
from .launch_30ch_run_summary_query import (list_30ch_run_summaries,
                                            load_30ch_run_summary)
from .launch_30ch_run_summary_artifacts import write_30ch_run_summary
from .run_manifest import build_run_manifest, write_run_manifest, next_run_id
from .anonymous_dialogue import AnonymousDialogueMatch, identify_speaker, score_dialogue_against_profile
from .body_pair_query import (list_body_pair_validation_reports,
                              load_body_pair_validation_report)
from .ab_cleaning_report import (build_ab_cleaning_report,
                                 AB_CLEANING_REPORT_KIND,
                                 AB_CLEANING_REPORT_VERSION)
from .quality_rubric import (QualityRubric, RubricDimension, build_quality_rubric,
                             render_quality_rubric_yaml, write_quality_rubric_file,
                             RUBRIC_ID, RUBRIC_VERSION, RUBRIC_FILENAME,
                             RUBRIC_DIMENSIONS, rubric_dimension_ids)
from .text_metrics import TextLengthMetrics, measure_text_length
from .text_language import LanguageMetrics, measure_text_language
from .workflow_scheduler import (WorkflowRunManifest, WorkflowManifestStore,
                                 WorkflowScheduler, workflow_scheduler)
from .artifact_catalog import (ARTIFACT_CATALOG_KIND, ARTIFACT_CATALOG_VERSION,
                               ARTIFACT_CATALOG_FILENAME, load_artifact_catalog,
                               catalog_sections, catalog_artifacts)
from .pipeline_state import (PipelineReport, project_pipeline,
                             STAGE_DRAFTED, STAGE_REVIEWED, STAGE_ASSESSED,
                             STAGE_APPROVED, STAGE_PUBLISHED)
from .reviewer_calibration import (DIMENSIONS, DECISION_DIMENSIONS,
                                   DIAGNOSTIC_DIMENSIONS,
                                   UNRELIABLE_DIMENSIONS,
                                   DIMENSION_LEVELS, RESULT_KIND,
                                   REPORT_KIND, REPORT_VERSION,
                                   build_calibration_row,
                                   build_calibration_summary,
                                   build_real_calibration_report,
                                   calibration_metadata_dir,
                                   load_calibration_results,
                                   load_calibration_subset,
                                   load_sample_body, load_sample_human_scores,
                                   write_calibration_results)
from .w9_calibration_summary import (build_w9_summary, write_w9_summary,
                                     render_w9_report, write_w9_report)
from .w9_policy import (build_w9_selection_policy, load_w9_dimension_policy,
                        classify_w9_dimension, can_use_w9_dimension_for_decision,
                        filter_w9_decision_scores)
from .reviewer_calibration_report import render_w9_summary_markdown, write_w9_summary_markdown
from .million_word_stability import build_million_word_stability_report
from .platform_feedback_reconciliation import reconcile_platform_feedback
from .commercial_calibration import build_commercial_calibration
from .multi_proposal_comparison import compare_multi_proposals
from ..director.compare import build_version_comparison, validate_version_comparison
from ..director.select import build_version_selection, validate_version_selection

__all__ = ["ChapterSpec", "ChapterRun", "SerialResult",
           "plan_chapters", "plan_continuation_from_rolling_plan", "run_serial",
           "load_serial_checkpoint", "load_serial_checkpoints",
           "backfill_checkpoints", "build_checkpoint", "CHECKPOINT_INDICES",
           "build_rolling_plan", "load_rolling_plan", "load_rolling_plans",
           "ROLLING_PLAN_CATEGORY",
           "build_run_manifest", "write_run_manifest", "next_run_id",
           "build_live_baseline_report", "write_live_baseline_report",
           "next_report_id",
           "build_precheck_environment", "build_precheck_report",
           "PRECHECK_BASELINE_ID",
           "LiveBaselineRunConfig", "build_live_baseline_config",
           "BASELINE_5CH_ID", "BASELINE_3CH_ID", "BASELINE_5CH_CHAPTERS",
           "BASELINE_3CH_CHAPTERS", "BASELINE_5CH_BUDGET_CNY",
           "BASELINE_3CH_BUDGET_CNY", "BASELINE_5CH_PROMPT_VERSION",
           "BASELINE_5CH_MODEL_PROVIDER", "BASELINE_5CH_MODEL_ID",
           "build_baseline_freeze_record", "write_baseline_freeze_record",
           "list_baseline_freeze_refs", "load_baseline_freeze_record",
           "FREEZE_KIND", "FREEZE_VERSION",
           "compare_baseline_freeze_records", "compare_baseline_freeze_paths",
           "COMPARISON_KIND", "COMPARISON_VERSION",
           "build_baseline_compare_report", "write_baseline_compare_report",
           "compare_and_write_baseline_report",
           "BASELINE_COMPARE_REPORT_CATEGORY",
           "BASELINE_COMPARE_REPORT_VERSION",
           "BASELINE_COMPARE_REPORT_KIND",
           "build_quality_snapshot", "compare_quality_snapshots",
           "QUALITY_SNAPSHOT_KIND", "QUALITY_SNAPSHOT_VERSION",
           "build_short_run_validation_report",
           "build_short_run_validation_report_from_bodies",
           "write_short_run_validation_report", "SHORT_RUN_VALIDATION_CATEGORY",
           "list_short_run_validation_reports", "load_short_run_validation_report",
           "VALIDATION_REPORT_KIND", "VALIDATION_REPORT_VERSION",
           "build_body_pair_validation_report", "BODY_PAIR_REPORT_KIND",
           "BODY_PAIR_REPORT_VERSION", "list_body_pair_validation_reports",
           "load_body_pair_validation_report",
           "build_ab_cleaning_report", "AB_CLEANING_REPORT_KIND",
           "AB_CLEANING_REPORT_VERSION", "build_ab_cleaning_flow",
           "write_ab_cleaning_flow",
           "list_ab_cleaning_reports", "load_ab_cleaning_report",
           "SpeechProfile", "build_speech_profile",
           "render_speech_profiles", "merge_speech_profiles", "coerce_speech_profile",
           "AnonymousDialogueMatch", "identify_speaker", "score_dialogue_against_profile",
           "QualityRubric", "RubricDimension", "build_quality_rubric",
           "render_quality_rubric_yaml", "write_quality_rubric_file",
           "RUBRIC_ID", "RUBRIC_VERSION", "RUBRIC_FILENAME",
           "RUBRIC_DIMENSIONS", "rubric_dimension_ids",
           "TextLengthMetrics", "measure_text_length",
           "LanguageMetrics", "measure_text_language",
           "ARTIFACT_CATALOG_KIND", "ARTIFACT_CATALOG_VERSION", "ARTIFACT_CATALOG_FILENAME",
           "load_artifact_catalog", "catalog_sections", "catalog_artifacts",
           "WorkflowRunManifest", "WorkflowManifestStore",
           "WorkflowScheduler", "workflow_scheduler",
           "build_golden_three_review_pack", "build_golden_three_review_record",
           "GOLDEN_THREE_RECORD_KIND", "GOLDEN_THREE_RECORD_VERSION",
           "list_golden_three_review_records", "load_golden_three_review_record",
           "write_winner_drift_report", "list_winner_drift_reports",
           "load_winner_drift_report",
           "build_baseline_report", "BASELINE_REPORT_KIND", "BASELINE_REPORT_VERSION",
           "write_baseline_report", "list_baseline_reports", "load_baseline_report",
           "build_30ch_launch_plan", "write_30ch_launch_plan",
           "build_30ch_launch_report", "write_30ch_launch_report",
           "LAUNCH_30CH_REPORT_KIND", "LAUNCH_30CH_REPORT_VERSION",
           "list_30ch_launch_reports", "load_30ch_launch_report",
           "build_30ch_launch_link", "build_30ch_run_attachment",
           "list_30ch_launch_bundle", "load_30ch_launch_bundle",
           "build_30ch_launch_summary",
           "write_30ch_launch_summary", "list_30ch_launch_summaries", "load_30ch_launch_summary",
           "build_run_aggregate",
           "write_run_aggregate", "list_run_aggregates", "load_run_aggregate",
           "write_30ch_run_summary", "list_30ch_run_summaries", "load_30ch_run_summary",
           "build_winner_drift_report",
           "PipelineReport", "project_pipeline",
           "STAGE_DRAFTED", "STAGE_REVIEWED", "STAGE_ASSESSED",
           "STAGE_APPROVED", "STAGE_PUBLISHED",
           "DIMENSIONS", "DECISION_DIMENSIONS", "DIAGNOSTIC_DIMENSIONS",
           "UNRELIABLE_DIMENSIONS", "DIMENSION_LEVELS",
           "RESULT_KIND", "REPORT_KIND", "REPORT_VERSION",
           "build_calibration_row", "build_calibration_summary",
           "build_real_calibration_report", "calibration_metadata_dir",
           "load_calibration_results", "load_calibration_subset",
           "load_sample_body", "load_sample_human_scores",
           "write_calibration_results", "build_w9_summary", "write_w9_summary",
           "render_w9_report", "write_w9_report",
           "load_w9_dimension_policy", "classify_w9_dimension",
           "can_use_w9_dimension_for_decision", "filter_w9_decision_scores",
           "build_w9_selection_policy",
           "build_version_comparison", "validate_version_comparison",
           "build_version_selection", "validate_version_selection",
           "build_million_word_stability_report", "reconcile_platform_feedback",
           "build_commercial_calibration", "compare_multi_proposals"]
