"""
P1 改进：增强版出口提取 - 支持独立置信度和证据定位

这是一个渐进式改进方案，不破坏现有 API。

核心思路：
1. 每个提取方法返回 (value, confidence, evidence_span)
2. extract_actual_exit_state 聚合所有字段的置信度
3. 低置信度字段可以标记或回退到计划值
"""

# 新的提取方法签名示例
def _extract_location_with_confidence(self, text: str, planned_location: str = None):
    """
    提取地点，返回值、置信度和证据

    Returns:
        (location_id, confidence, evidence_span)

    confidence:
        1.0 - 匹配到配置的关键词
        0.7 - 从计划地点 ID 提取的关键词在文中找到
        0.5 - 使用计划地点作为回退
        0.3 - 返回 loc_unknown
    """
    location_keywords = self.config.get('location_keywords', {})

    # 方法 1: 配置关键词匹配（高置信度）
    for loc_id, keywords in location_keywords.items():
        for keyword in keywords:
            if keyword in text:
                # 找到关键词位置
                idx = text.find(keyword)
                evidence = text[max(0, idx-20):min(len(text), idx+len(keyword)+20)]
                return loc_id, 1.0, {"text": evidence, "match": keyword}

    # 方法 2: 从计划地点提取关键词（中等置信度）
    if planned_location:
        fallback = self.config.get('fallback', {})
        if fallback.get('auto_extract_from_id', True):
            id_str = planned_location
            if fallback.get('strip_loc_prefix', True):
                id_str = id_str.replace('loc_', '')
            keywords = id_str.split(fallback.get('id_separator', '_'))
            for kw in keywords:
                if kw in text:
                    idx = text.find(kw)
                    evidence = text[max(0, idx-20):min(len(text), idx+len(kw)+20)]
                    return planned_location, 0.7, {"text": evidence, "match": kw}

        # 方法 3: 回退到计划地点（低置信度）
        return planned_location, 0.5, {"text": "", "match": "planned_fallback"}

    # 方法 4: 未知（极低置信度）
    return 'loc_unknown', 0.3, {"text": "", "match": "none"}


def _extract_characters_with_confidence(self, text: str, planned_characters: list = None):
    """
    提取在场人物，返回列表、置信度和证据

    Returns:
        (characters, confidence, evidence_spans)
    """
    # 固定角色名列表（应从配置或 facts 读取）
    known_characters = ['主角', '导师', '师父', '师兄', '师姐', '长老', '掌门']

    found_characters = []
    evidence_spans = []

    for char in known_characters:
        if char in text:
            idx = text.find(char)
            evidence = text[max(0, idx-20):min(len(text), idx+len(char)+20)]
            found_characters.append(char)
            evidence_spans.append({"text": evidence, "character": char})

    if found_characters:
        # 找到至少一个角色（中高置信度）
        confidence = 0.8
    elif planned_characters:
        # 没找到但有计划角色（低置信度）
        found_characters = planned_characters
        confidence = 0.4
    else:
        # 完全未知（极低置信度）
        confidence = 0.2

    return found_characters, confidence, evidence_spans


def _extract_emotional_state_with_confidence(self, text: str):
    """
    提取情绪状态，返回值、置信度和证据

    Returns:
        (emotion, confidence, evidence_span)
    """
    emotion_keywords = {
        'determined': ['坚定', '决心', '果断'],
        'fearful': ['恐惧', '害怕', '惊恐'],
        'hopeful': ['希望', '期待', '憧憬'],
        'desperate': ['绝望', '无助', '放弃'],
        'calm': ['平静', '淡然', '从容'],
        'tense': ['紧张', '焦虑', '不安'],
    }

    for emotion, keywords in emotion_keywords.items():
        for keyword in keywords:
            if keyword in text:
                idx = text.find(keyword)
                evidence = text[max(0, idx-20):min(len(text), idx+len(keyword)+20)]
                return emotion, 0.9, {"text": evidence, "match": keyword}

    # 未找到明确情绪关键词
    return 'neutral', 0.4, {"text": "", "match": "none"}


def _extract_hook_promise_with_confidence(self, text: str):
    """
    提取章末钩子承诺，返回值、置信度和证据

    Returns:
        (hook_text, confidence, evidence_span)
    """
    # 钩子通常在最后几句
    last_sentences = text[-200:]

    hook_indicators = ['但是', '然而', '忽然', '突然', '这时', '就在此时']

    for indicator in hook_indicators:
        if indicator in last_sentences:
            idx = last_sentences.find(indicator)
            hook_text = last_sentences[idx:]
            return hook_text, 0.7, {"text": hook_text, "indicator": indicator}

    # 没有明确钩子指示词，返回最后一句
    if len(last_sentences) > 0:
        return last_sentences[-100:], 0.4, {"text": last_sentences[-100:], "indicator": "last_sentence"}

    return "", 0.2, {"text": "", "indicator": "none"}


# 增强版的 extract_actual_exit_state
def extract_actual_exit_state_enhanced(
    self,
    chapter: int,
    final_text: str,
    final_text_hash: str
) -> dict:
    """
    增强版：从最终正文提取实际出口状态，包含每个字段的置信度和证据

    Returns:
        {
            "chapter": int,
            "final_text_hash": str,
            "location_id": str,
            "location_confidence": float,
            "characters_present": [str],
            "characters_confidence": float,
            "emotional_state": str,
            "emotional_confidence": float,
            "hook_promise": str,
            "hook_confidence": float,
            "evidence_spans": [
                {"field": "location_id", "text": str, "confidence": float},
                {"field": "characters_present", "text": str, "confidence": float},
                ...
            ],
            "overall_confidence": float,  # 所有字段的平均置信度
            "extraction_method": "heuristic_enhanced",
            "extracted_at": str
        }
    """
    from datetime import datetime, timezone

    # 加载契约
    contract = self._load_contract(chapter)
    planned_exit = contract.get('exit_target', {}) if contract else {}

    text_len = len(final_text)
    last_portion = final_text[int(text_len * 0.8):]

    # 提取各字段（带置信度）
    location, loc_conf, loc_evidence = self._extract_location_with_confidence(
        last_portion, planned_exit.get('location_id'))

    characters, char_conf, char_evidence = self._extract_characters_with_confidence(
        last_portion, planned_exit.get('characters_present'))

    emotion, emo_conf, emo_evidence = self._extract_emotional_state_with_confidence(
        last_portion)

    hook, hook_conf, hook_evidence = self._extract_hook_promise_with_confidence(
        last_portion)

    # 构建 evidence_spans
    evidence_spans = []

    if loc_evidence.get("text"):
        evidence_spans.append({
            "field": "location_id",
            "text": loc_evidence["text"],
            "confidence": loc_conf,
            "match": loc_evidence.get("match")
        })

    for char_ev in char_evidence:
        evidence_spans.append({
            "field": "characters_present",
            "text": char_ev["text"],
            "confidence": char_conf,
            "character": char_ev["character"]
        })

    if emo_evidence.get("text"):
        evidence_spans.append({
            "field": "emotional_state",
            "text": emo_evidence["text"],
            "confidence": emo_conf,
            "match": emo_evidence.get("match")
        })

    if hook_evidence.get("text"):
        evidence_spans.append({
            "field": "hook_promise",
            "text": hook_evidence["text"],
            "confidence": hook_conf,
            "indicator": hook_evidence.get("indicator")
        })

    # 计算总体置信度（加权平均）
    overall_confidence = (loc_conf * 0.3 + char_conf * 0.3 +
                         emo_conf * 0.2 + hook_conf * 0.2)

    actual_exit = {
        "chapter": chapter,
        "final_text_hash": final_text_hash,
        "location_id": location,
        "location_confidence": loc_conf,
        "characters_present": characters,
        "characters_confidence": char_conf,
        "emotional_state": emotion,
        "emotional_confidence": emo_conf,
        "hook_promise": hook,
        "hook_confidence": hook_conf,
        "evidence_spans": evidence_spans,
        "overall_confidence": overall_confidence,
        "extraction_method": "heuristic_enhanced",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }

    return actual_exit
