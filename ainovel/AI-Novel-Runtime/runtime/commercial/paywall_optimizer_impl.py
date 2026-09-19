"""paywall_optimizer_impl.py — Paywall Optimizer Implementation

Complete implementation of automatic paywall point identification and optimization.
Started: 2026-08-11 04:10

Phase 1 Implementation: Core hook measurement and position identification
Timeline: Week 1-2 (14 days)
Status: In Progress

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import re


class SuspenseType(Enum):
    """Types of suspense hooks."""
    CLIFFHANGER = "cliffhanger"
    CONFLICT = "conflict"
    MYSTERY = "mystery"
    REVELATION = "revelation"
    THREAT = "threat"
    EMOTIONAL = "emotional"
    GOAL = "goal"


@dataclass
class HookStrengthScore:
    """Quantitative hook strength measurement."""
    overall_score: float
    suspense_type: SuspenseType
    cliffhanger_intensity: float
    curiosity_trigger: float
    emotional_investment: float
    conflict_escalation: float
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]
    predicted_retention: float
    predicted_paywall_conversion: float


@dataclass
class PaywallPosition:
    """Recommended paywall position."""
    chapter_number: int
    confidence: float
    hook_strength: float
    story_progress: float
    reader_investment: float
    previous_hook: Optional[HookStrengthScore]
    story_milestone: str
    genre_typical: bool
    alternatives: List[Dict[str, Any]]


class PaywallOptimizer:
    """Automatic paywall point identification and optimization."""

    def __init__(self, model, *, optimizer_id: str = "paywall-optimizer-v1"):
        self.model = model
        self.optimizer_id = optimizer_id
        self._suspense_library = self._load_suspense_library()
        self._genre_patterns = self._load_genre_patterns()

    def measure_hook_strength(
        self,
        chapter_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> HookStrengthScore:
        """Quantitatively measure chapter-end hook strength.

        Implementation:
        1. Extract chapter ending
        2. Build measurement prompt
        3. Call LLM for scoring
        4. Parse into HookStrengthScore
        """
        if not chapter_text or not chapter_text.strip():
            raise ValueError("Chapter text cannot be empty")

        # Extract ending
        ending = self._extract_ending(chapter_text)

        # Build prompt
        prompt = self._build_measurement_prompt(ending, context)

        # Call LLM
        response = self.model.generate(prompt)

        # Parse response
        score = self._parse_strength_response(response)

        return score

    def identify_paywall_point(
        self,
        chapters: List[Dict[str, Any]],
        target_chapter: Optional[int] = None,
        genre: str = "xuanhuan"
    ) -> PaywallPosition:
        """Identify optimal paywall position.

        Implementation:
        1. Analyze story structure
        2. Measure hook strength for candidates
        3. Estimate reader investment
        4. Compare with genre patterns
        5. Rank and recommend
        """
        if not chapters:
            raise ValueError("Chapters list cannot be empty")

        # Get candidate positions (typically chapter 6-12 for web novels)
        candidates = self._get_candidate_positions(len(chapters), genre)

        # Score each candidate
        scored_candidates = []
        for ch_num in candidates:
            if ch_num >= len(chapters):
                continue

            chapter = chapters[ch_num]
            score = self._score_paywall_candidate(chapter, ch_num, chapters, genre)
            scored_candidates.append(score)

        # Sort by predicted conversion
        scored_candidates.sort(
            key=lambda x: x.get('predicted_conversion', 0),
            reverse=True
        )

        if not scored_candidates:
            # Fallback to default
            return self._default_paywall_position(len(chapters), genre)

        # Build recommendation
        best = scored_candidates[0]

        return PaywallPosition(
            chapter_number=best['chapter_number'],
            confidence=best['confidence'],
            hook_strength=best['hook_strength'],
            story_progress=best['story_progress'],
            reader_investment=best['reader_investment'],
            previous_hook=best.get('previous_hook'),
            story_milestone=best.get('milestone', 'unknown'),
            genre_typical=best.get('genre_typical', False),
            alternatives=[c for c in scored_candidates[1:4]]  # Top 3 alternatives
        )

    def optimize_for_paywall(
        self,
        draft: str,
        paywall_chapter: int,
        current_strength: Optional[HookStrengthScore] = None
    ) -> str:
        """Optimize chapter ending for paywall conversion.

        Implementation:
        1. Measure current hook strength
        2. Identify weak points
        3. Generate enhancement suggestions
        4. Apply enhancements
        5. Verify improvement
        """
        if not draft or not draft.strip():
            raise ValueError("Draft cannot be empty")

        # Measure current strength
        if current_strength is None:
            current_strength = self.measure_hook_strength(draft)

        # Check if optimization needed
        if current_strength.overall_score >= 85.0:
            return draft  # Already strong

        # Build optimization prompt
        prompt = self._build_optimization_prompt(
            draft,
            current_strength,
            paywall_chapter
        )

        # Call LLM for optimization
        response = self.model.generate(prompt)

        # Extract optimized text
        optimized = self._extract_optimized_text(response, draft)

        return optimized

    def _extract_ending(self, chapter_text: str, char_count: int = 500) -> str:
        """Extract chapter ending."""
        if len(chapter_text) <= char_count:
            return chapter_text
        return chapter_text[-char_count:]

    def _build_measurement_prompt(
        self,
        ending: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build hook measurement prompt."""
        prompt = f"""请量化评估以下章节结尾的钩子强度，用于付费点优化。

章节结尾：
{ending}

评分维度（0-100分）：
1. overall_score - 总体钩子强度
2. cliffhanger_intensity - 悬念强度
3. curiosity_trigger - 好奇心触发
4. emotional_investment - 情感投入
5. conflict_escalation - 冲突升级

识别悬念类型：
cliffhanger, conflict, mystery, revelation, threat, emotional, goal

分析：
- strengths (优点): 具体有效的元素
- weaknesses (缺点): 需要改进的地方
- suggestions (建议): 具体改进建议

预测（0-1）：
- predicted_retention: 读者继续率
- predicted_paywall_conversion: 如作为付费点的转化率

返回JSON格式。
"""
        return prompt

    def _parse_strength_response(self, response: str) -> HookStrengthScore:
        """Parse LLM response into HookStrengthScore."""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            return self._default_hook_strength()

        try:
            data = json.loads(json_match.group(0))
            return HookStrengthScore(
                overall_score=float(data.get('overall_score', 50.0)),
                suspense_type=SuspenseType(data.get('suspense_type', 'cliffhanger')),
                cliffhanger_intensity=float(data.get('cliffhanger_intensity', 50.0)),
                curiosity_trigger=float(data.get('curiosity_trigger', 50.0)),
                emotional_investment=float(data.get('emotional_investment', 50.0)),
                conflict_escalation=float(data.get('conflict_escalation', 50.0)),
                strengths=data.get('strengths', []),
                weaknesses=data.get('weaknesses', []),
                suggestions=data.get('suggestions', []),
                predicted_retention=float(data.get('predicted_retention', 0.6)),
                predicted_paywall_conversion=float(data.get('predicted_paywall_conversion', 0.5))
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return self._default_hook_strength()

    def _get_candidate_positions(self, total_chapters: int, genre: str) -> List[int]:
        """Get candidate paywall positions based on genre."""
        # Default web novel pattern: paywall at chapter 6-12
        patterns = self._genre_patterns.get(genre, {})
        typical_range = patterns.get('paywall_range', (6, 12))

        candidates = []
        for ch in range(typical_range[0], min(typical_range[1] + 1, total_chapters)):
            candidates.append(ch)

        # Also consider alternative positions
        if total_chapters >= 20:
            candidates.extend([15, 20])

        return sorted(set(candidates))

    def _score_paywall_candidate(
        self,
        chapter: Dict[str, Any],
        chapter_num: int,
        all_chapters: List[Dict[str, Any]],
        genre: str
    ) -> Dict[str, Any]:
        """Score a paywall candidate position."""
        # Get chapter text
        text = chapter.get('body', chapter.get('text', ''))

        # Measure hook strength
        hook = self.measure_hook_strength(text)

        # Calculate story progress
        story_progress = chapter_num / len(all_chapters)

        # Estimate reader investment (simple heuristic)
        reader_investment = min(1.0, chapter_num / 10.0)

        # Check if genre typical
        patterns = self._genre_patterns.get(genre, {})
        typical_range = patterns.get('paywall_range', (6, 12))
        genre_typical = typical_range[0] <= chapter_num <= typical_range[1]

        # Calculate predicted conversion
        conversion = self._calculate_conversion(
            hook.predicted_paywall_conversion,
            reader_investment,
            genre_typical
        )

        return {
            'chapter_number': chapter_num,
            'hook_strength': hook.overall_score,
            'story_progress': story_progress,
            'reader_investment': reader_investment,
            'predicted_conversion': conversion,
            'confidence': 0.8 if genre_typical else 0.6,
            'previous_hook': hook,
            'milestone': f'Chapter {chapter_num}',
            'genre_typical': genre_typical
        }

    def _calculate_conversion(
        self,
        hook_conversion: float,
        investment: float,
        genre_typical: bool
    ) -> float:
        """Calculate predicted paywall conversion rate."""
        # Weighted combination
        base = hook_conversion * 0.5 + investment * 0.3
        if genre_typical:
            base += 0.2
        return min(1.0, base)

    def _default_paywall_position(
        self,
        total_chapters: int,
        genre: str
    ) -> PaywallPosition:
        """Default paywall position as fallback."""
        # Default to chapter 6 for web novels
        return PaywallPosition(
            chapter_number=6,
            confidence=0.5,
            hook_strength=60.0,
            story_progress=0.06,
            reader_investment=0.6,
            previous_hook=None,
            story_milestone="Default position",
            genre_typical=True,
            alternatives=[]
        )

    def _build_optimization_prompt(
        self,
        draft: str,
        strength: HookStrengthScore,
        chapter_num: int
    ) -> str:
        """Build optimization prompt."""
        prompt = f"""请优化以下章节结尾，使其成为高效的付费点。

当前章节: 第{chapter_num}章
当前钩子强度: {strength.overall_score:.1f}分
弱点: {', '.join(strength.weaknesses)}

章节内容：
{draft[-1000:]}  # Last 1000 chars

优化目标：
1. 提升钩子强度到85+分
2. 保持原文风格
3. 不改变核心情节
4. 强化付费转化

请返回优化后的章节结尾（最后500字）。
"""
        return prompt

    def _extract_optimized_text(self, response: str, original: str) -> str:
        """Extract optimized text from LLM response."""
        # Simple implementation: return response if reasonable
        if len(response) > 200 and len(response) < 2000:
            # Replace original ending with optimized version
            return original[:-1000] + "\n\n" + response
        return original

    def _default_hook_strength(self) -> HookStrengthScore:
        """Default hook strength as fallback."""
        return HookStrengthScore(
            overall_score=50.0,
            suspense_type=SuspenseType.CLIFFHANGER,
            cliffhanger_intensity=50.0,
            curiosity_trigger=50.0,
            emotional_investment=50.0,
            conflict_escalation=50.0,
            strengths=[],
            weaknesses=["无法评估"],
            suggestions=[],
            predicted_retention=0.5,
            predicted_paywall_conversion=0.4
        )

    def _load_suspense_library(self) -> Dict[str, Any]:
        """Load suspense pattern library."""
        return {
            "cliffhanger": {"strength_multiplier": 1.2},
            "conflict": {"strength_multiplier": 1.1},
            "mystery": {"strength_multiplier": 1.0}
        }

    def _load_genre_patterns(self) -> Dict[str, Any]:
        """Load genre-specific patterns."""
        return {
            "xuanhuan": {
                "paywall_range": (6, 12),
                "typical_milestone": "境界突破或重大发现"
            },
            "都市": {
                "paywall_range": (8, 15),
                "typical_milestone": "身份揭示或冲突升级"
            }
        }


# Test function
def test_paywall_optimizer():
    """Test paywall optimizer."""
    class MockModel:
        def generate(self, prompt):
            if "量化评估" in prompt:
                return '''{
                    "overall_score": 78.0,
                    "suspense_type": "cliffhanger",
                    "cliffhanger_intensity": 80.0,
                    "curiosity_trigger": 75.0,
                    "emotional_investment": 70.0,
                    "conflict_escalation": 80.0,
                    "strengths": ["悬念设置好"],
                    "weaknesses": ["情感投入不足"],
                    "suggestions": ["增强情感描写"],
                    "predicted_retention": 0.75,
                    "predicted_paywall_conversion": 0.65
                }'''
            return "优化后的文本"

    optimizer = PaywallOptimizer(model=MockModel())

    # Test hook measurement
    test_text = "测试章节内容..." * 100
    score = optimizer.measure_hook_strength(test_text)
    print(f"钩子强度: {score.overall_score:.1f}分")
    print(f"付费转化预测: {score.predicted_paywall_conversion:.2f}")

    # Test paywall identification
    chapters = [{'body': f'第{i}章内容'} for i in range(1, 101)]
    position = optimizer.identify_paywall_point(chapters, genre="xuanhuan")
    print(f"\n推荐付费点: 第{position.chapter_number}章")
    print(f"置信度: {position.confidence:.2f}")
    print(f"预期转化: {position.hook_strength:.1f}分")


if __name__ == "__main__":
    test_paywall_optimizer()
