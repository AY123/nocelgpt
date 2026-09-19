"""
契约门禁系统

提供契约的加载、验证和门禁功能
"""

from pathlib import Path
import json
import jsonschema
from typing import Optional
from enum import Enum


class ContractCheckError(Exception):
    """契约检查失败异常"""
    pass


class ContractViolationError(Exception):
    """严格模式下的契约违规异常"""
    pass


class ChapterStatus(Enum):
    """章节状态枚举（P2 严格模式）"""
    PRODUCED = "produced"
    CONTRACT_WARNING = "contract_warning"
    CONTRACT_INVALID = "contract_invalid"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"


class ContractGate:
    """
    契约门禁系统

    负责：
    1. 生成前检查（precheck）
    2. 契约加载
    3. 契约注入到prompt
    4. 生成后验证
    """

    def __init__(self, contracts_dir: Path, schemas_dir: Path, config_file: Optional[Path] = None, strict_mode: bool = False):
        """
        初始化契约门禁

        Args:
            contracts_dir: 契约目录
            schemas_dir: Schema目录
            config_file: 配置文件路径（可选，Task 3.1）
            strict_mode: 是否启用严格模式（P2，默认 False）
        """
        self.contracts_dir = Path(contracts_dir)
        self.schemas_dir = Path(schemas_dir)
        self.schema = self._load_schema()
        self.strict_mode = strict_mode

        # Task 3.1: 加载验证配置
        self.config = self._load_config(config_file)

        # P2: 严格模式配置
        self.strict_config = {
            "confidence_threshold": 0.7,  # 低于此阈值触发人工审核
            "block_critical_deviations": True,  # 阻断关键偏差
            "block_low_confidence": True,  # 阻断低置信度
        }

    def _load_config(self, config_file: Optional[Path]) -> dict:
        """加载验证配置文件（Task 3.1）.

        Args:
            config_file: 配置文件路径

        Returns:
            配置字典，如果加载失败则返回默认配置
        """
        # 尝试加载配置文件
        if config_file and Path(config_file).exists():
            try:
                import yaml
                with open(config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception:
                pass  # 加载失败，使用默认配置

        # 尝试默认位置
        default_config = self.contracts_dir / 'contract_validation_config.yaml'
        if default_config.exists():
            try:
                import yaml
                with open(default_config, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception:
                pass

        # 返回默认配置（向后兼容）
        return {
            'location_keywords': {},
            'validation_strategy': {
                'location_check_portion': 0.33,
                'hook_consumption_portion': 0.30,
                'hook_setup_portion': 0.20,
            },
            'strictness': {
                'location_mismatch': 'critical',
                'hook_not_consumed': 'critical',
                'required_character_missing': 'major',
                'end_hook_missing': 'major',
            },
            'fallback': {
                'auto_extract_from_id': True,
                'id_separator': '_',
                'strip_loc_prefix': True,
            }
        }

    def _load_schema(self) -> dict:
        """加载契约Schema"""
        schema_file = self.schemas_dir / 'chapter_contract.schema.json'

        if not schema_file.exists():
            raise FileNotFoundError(f"Schema文件不存在: {schema_file}")

        with open(schema_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_contract(self, chapter: int) -> Optional[dict]:
        """
        加载契约

        Returns:
            契约字典，如果不存在则返回None
        """
        contract_file = self.contracts_dir / f'chapter_{chapter:03d}_contract.json'

        if not contract_file.exists():
            return None

        with open(contract_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _check_source_staleness(self, contract: dict) -> Optional[str]:
        """检查契约的 source 是否过期（Task 3.2）.

        对比 contract.sources.content_hash 与当前 source 的实际 hash。
        如果不匹配，返回警告消息；如果匹配或无法检查，返回 None。

        这是 advisory 检查，不会 gate 生产流程（ADR-003）。

        Args:
            contract: 契约字典

        Returns:
            警告消息（如果过期），否则 None
        """
        sources = contract.get('sources', {})
        stored_hash = sources.get('content_hash')

        # 如果契约没有 content_hash，无法检查，跳过
        if not stored_hash:
            return None

        # 检查 outline_ref
        outline_ref = sources.get('outline_ref')
        if outline_ref:
            current_hash = self._compute_outline_hash(outline_ref)
            if current_hash and current_hash != stored_hash:
                return (
                    f"契约可能过期: sources.content_hash 不匹配。"
                    f"契约记录: {stored_hash[:16]}..., "
                    f"当前 outline: {current_hash[:16]}... "
                    f"建议重新生成契约。"
                )

        # 检查 based_on_chapter
        based_on = sources.get('based_on_chapter')
        if based_on:
            # 这里可以检查前章的 draft hash 是否变化
            # 但这需要访问 registry，暂时只做简单提示
            # 未来可以扩展为检查 derived/drafts/TASK-xxxxx.json
            pass

        # 没有发现过期
        return None

    def _compute_outline_hash(self, outline_ref: str) -> Optional[str]:
        """计算 outline 文件的当前 hash.

        Args:
            outline_ref: outline 文件引用

        Returns:
            当前 hash，如果文件不存在则返回 None
        """
        # 尝试多个可能的路径
        possible_paths = [
            self.contracts_dir.parent / outline_ref,
            self.contracts_dir.parent / 'sources' / outline_ref,
            Path(outline_ref),  # 绝对路径
        ]

        for path in possible_paths:
            if path.exists():
                import hashlib
                with open(path, 'rb') as f:
                    content = f.read()
                    return hashlib.sha256(content).hexdigest()

        # 文件不存在，无法计算
        return None

    def precheck(self, chapter: int) -> None:
        """
        生成前检查

        检查项：
        1. 契约文件存在
        2. Schema合规
        3. 已批准

        不通过则抛ContractCheckError

        Args:
            chapter: 章节号

        Raises:
            ContractCheckError: 检查失败
        """
        # 1. 契约存在
        contract = self._load_contract(chapter)
        if not contract:
            raise ContractCheckError(
                f"Ch{chapter}契约不存在: contracts/chapter_{chapter:03d}_contract.json"
            )

        # 2. Schema验证
        try:
            jsonschema.validate(instance=contract, schema=self.schema)
        except jsonschema.ValidationError as e:
            raise ContractCheckError(
                f"Ch{chapter}契约Schema验证失败: {e.message}\n"
                f"路径: {'.'.join(map(str, e.path))}"
            )
        except jsonschema.SchemaError as e:
            raise ContractCheckError(f"Schema本身有错误: {e.message}")

        # 3. 批准检查
        if not contract.get('approved'):
            raise ContractCheckError(
                f"Ch{chapter}契约未批准 (approved=false)"
            )

        # 4. Source Hash 过期检测（Task 3.2, advisory only）
        # 检查契约的 sources.content_hash 是否与当前 source 匹配
        # 如果不匹配，发出警告但不 gate（ADR-003）
        staleness_warning = self._check_source_staleness(contract)
        if staleness_warning:
            # 记录警告但不抛出异常（advisory）
            import logging
            logging.warning(f"Ch{chapter} {staleness_warning}")
            # 可以将警告添加到契约对象中供调用者使用
            contract['_staleness_warning'] = staleness_warning

        # 通过
        return

    def load_contract(self, chapter: int) -> dict:
        """
        加载契约（不检查）

        Args:
            chapter: 章节号

        Returns:
            契约字典

        Raises:
            FileNotFoundError: 契约不存在
        """
        contract = self._load_contract(chapter)
        if not contract:
            raise FileNotFoundError(
                f"Ch{chapter}契约不存在"
            )
        return contract

    def inject_contract(self, base_prompt: str, contract: dict) -> str:
        """
        将契约注入到prompt

        在base_prompt前添加契约要求部分

        Args:
            base_prompt: 原始prompt
            contract: 契约字典

        Returns:
            注入契约后的完整prompt
        """
        entry = contract.get('entry_state', {})
        intent = contract.get('chapter_intent', {})
        exit_target = contract.get('exit_target', {})

        # 格式化地点ID
        def format_location(loc_id: str) -> str:
            if not loc_id:
                return "（待定义）"
            return loc_id.replace('loc_', '').replace('_', ' ')

        contract_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 章节契约（必须严格遵守）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【入口要求】
• 地点：{format_location(entry.get('location_id', ''))}
• 时间关系：{entry.get('time_relation', '未指定')}
• 视角：{entry.get('pov', '未指定')}
• 在场人物：{', '.join(entry.get('required_characters', []))}

上一章钩子（必须在前20%消费）：
{entry.get('must_address', '无')}

【本章目标】
{intent.get('objective', '未定义')}

主要冲突：
{intent.get('main_conflict', '未定义')}

必须产生的不可逆变化：
{intent.get('irreversible_change', '未定义')}

【出口要求】
• 结束地点：{format_location(exit_target.get('location_id', ''))}
• 在场人物：{', '.join(exit_target.get('characters_present', []))}

未完成动作（留给下一章）：
{exit_target.get('unfinished_action', '无')}

章末钩子（必须设置）：
{exit_target.get('hook_promise', '无')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 契约遵守检查清单
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

生成后请确认：
□ 开头符合入口要求（地点、时间、视角、人物）
□ 前20%处理了上章钩子
□ 实现了本章目标和不可逆变化
□ 结尾符合出口要求
□ 设置了明确的章末钩子

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        return contract_section + "\n" + base_prompt

    def validate_chain(self, prev_chapter: int, curr_chapter: int) -> dict:
        """
        验证相邻契约的连续性

        检查前一章的 exit_target 与当前章的 entry_state 是否一致

        Args:
            prev_chapter: 前一章章节号
            curr_chapter: 当前章章节号

        Returns:
            {
                "valid": bool,
                "issues": [
                    {
                        "field": str,
                        "prev_value": any,
                        "curr_value": any,
                        "description": str
                    }
                ]
            }

        Raises:
            FileNotFoundError: 契约不存在
        """
        prev_contract = self._load_contract(prev_chapter)
        curr_contract = self._load_contract(curr_chapter)

        if not prev_contract:
            raise FileNotFoundError(f"Ch{prev_chapter}契约不存在")
        if not curr_contract:
            raise FileNotFoundError(f"Ch{curr_chapter}契约不存在")

        prev_exit = prev_contract.get('exit_target', {})
        curr_entry = curr_contract.get('entry_state', {})

        issues = []

        # 1. 检查地点连续性
        prev_location = prev_exit.get('location_id', '')
        curr_location = curr_entry.get('location_id', '')
        if prev_location and curr_location and prev_location != curr_location:
            # 允许地点变化，但必须在 transition_to_next 中声明
            transition = prev_contract.get('transition_to_next', {})
            location_change = transition.get('location_change')
            if not location_change:
                issues.append({
                    "field": "location",
                    "prev_value": prev_location,
                    "curr_value": curr_location,
                    "description": f"地点从 {prev_location} 变为 {curr_location}，但前章未声明地点变化"
                })

        # 2. 检查钩子连续性
        prev_hook_id = prev_exit.get('hook_id', '')
        curr_hook_to_consume = curr_entry.get('hook_to_consume', '')
        if prev_hook_id and not curr_hook_to_consume:
            issues.append({
                "field": "hook",
                "prev_value": prev_hook_id,
                "curr_value": None,
                "description": f"前章设置了钩子 {prev_hook_id}，但当前章未声明要消费它"
            })
        elif prev_hook_id and curr_hook_to_consume and prev_hook_id != curr_hook_to_consume:
            issues.append({
                "field": "hook",
                "prev_value": prev_hook_id,
                "curr_value": curr_hook_to_consume,
                "description": f"前章钩子 {prev_hook_id} 与当前章要消费的钩子 {curr_hook_to_consume} 不匹配"
            })

        # 3. 检查必须处理的内容
        prev_unfinished = prev_exit.get('unfinished_action', '')
        curr_must_address = curr_entry.get('must_address', '')
        if prev_unfinished and not curr_must_address:
            issues.append({
                "field": "unfinished_action",
                "prev_value": prev_unfinished,
                "curr_value": None,
                "description": "前章有未完成动作，但当前章未声明要处理"
            })

        # 4. 检查人物连续性
        prev_characters = set(prev_exit.get('characters_present', []))
        curr_characters = set(curr_entry.get('required_characters', []))
        # 允许人物增减，但如果前章结尾有人，当前章开头应该至少有部分交集
        # 除非明确声明了场景切换
        if prev_characters and curr_characters:
            intersection = prev_characters & curr_characters
            transition = prev_contract.get('transition_to_next', {})
            scene_continuity = transition.get('scene_continuity', '')
            if not intersection and scene_continuity != 'cut':
                issues.append({
                    "field": "characters",
                    "prev_value": list(prev_characters),
                    "curr_value": list(curr_characters),
                    "description": f"前章结尾人物 {prev_characters} 与当前章开头人物 {curr_characters} 完全不重叠，且未声明场景切换"
                })

        # 5. 检查 POV 连续性
        transition = prev_contract.get('transition_to_next', {})
        pov_change = transition.get('pov_change', False)
        curr_pov = curr_entry.get('pov', '')
        # 如果声明了 POV 变化，当前章 POV 应该不同（这个检查需要前章的 POV，暂时简化）
        # 这里只检查：如果没有声明 POV 变化，且前章结尾人物和当前章开头人物有交集，
        # 则 POV 应该保持一致（需要前章 POV 信息，暂时跳过）

        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

    def validate(
        self,
        chapter: int,
        prev_text: str,
        curr_text: str
    ) -> dict:
        """
        生成后验证

        验证当前章节是否遵守契约

        Args:
            chapter: 当前章节号
            prev_text: 上一章正文
            curr_text: 当前章正文

        Returns:
            {
                "valid": bool,
                "hard_errors": [],
                "soft_issues": []
            }
        """
        # 导入验证器（避免循环依赖）
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'tools'))
        from validate_contract import ContractValidator

        validator = ContractValidator(str(self.contracts_dir))
        return validator.validate_transition(
            chapter - 1,
            chapter,
            prev_text,
            curr_text
        )

    def check_candidate(
        self,
        chapter: int,
        candidate_text: str,
        prev_text: str = ""
    ) -> dict:
        """
        Candidate 阶段契约检查（简化版）

        检查候选文本是否满足契约的关键要求，用于决定是否需要修订。
        只检查 Critical 级别的问题：地点、钩子、必需人物。

        Args:
            chapter: 章节号
            candidate_text: 候选文本
            prev_text: 上一章正文（用于连续性检查）

        Returns:
            {
                "pass": bool,
                "issues": [
                    {
                        "category": "critical" | "major" | "minor",
                        "field": str,
                        "description": str
                    }
                ],
                "requires_revision": bool,
                "revision_suggestions": [str]
            }
        """
        contract = self._load_contract(chapter)
        if not contract:
            return {
                "pass": False,
                "issues": [{"category": "critical", "field": "contract", "description": "Contract not found"}],
                "requires_revision": False,  # 没有契约就不检查
                "revision_suggestions": []
            }

        issues = []
        suggestions = []
        entry_state = contract.get('entry_state', {})
        exit_target = contract.get('exit_target', {})

        # Critical Check 1: 地点匹配（入口）
        required_location = entry_state.get('location_id', '')
        if required_location and required_location != 'loc_unknown':
            # 简化检查：在文本中寻找地点关键词
            location_found = self._check_location_in_text(candidate_text, required_location)
            if not location_found:
                issues.append({
                    "category": "critical",
                    "field": "entry_location",
                    "description": f"章节未在要求的地点 {required_location} 开始"
                })
                suggestions.append(f"确保章节在 {required_location} 开始")

        # Critical Check 2: 钩子消费（Chapter 2+）
        if chapter > 1:
            hook_to_consume = entry_state.get('hook_to_consume', '')
            must_address = entry_state.get('must_address', '')
            if hook_to_consume or must_address:
                # 简化检查：在前 30% 的文本中寻找相关内容
                first_third = candidate_text[:len(candidate_text) // 3]
                # 提取关键词进行检查（简化版）
                if must_address and len(must_address) > 5:
                    # 取 must_address 中的关键词
                    keywords = [w for w in must_address.split() if len(w) > 2][:3]
                    found_any = any(kw in first_third for kw in keywords)
                    if not found_any:
                        issues.append({
                            "category": "critical",
                            "field": "hook_consumption",
                            "description": f"前 30% 未处理上章钩子: {must_address[:50]}..."
                        })
                        suggestions.append("在章节前 30% 处理上一章的钩子")

        # Critical Check 3: 必需人物（入口）
        required_characters = entry_state.get('required_characters', [])
        if required_characters:
            # 简化检查：在前 20% 寻找角色 ID 或名字
            first_fifth = candidate_text[:len(candidate_text) // 5]
            missing_characters = []
            for char_id in required_characters:
                # 检查 char_id 或从契约中提取的角色名
                if char_id not in first_fifth:
                    missing_characters.append(char_id)

            if missing_characters:
                issues.append({
                    "category": "major",  # Major 而非 Critical，因为角色可能用名字而非ID
                    "field": "required_characters",
                    "description": f"开头可能缺少必需角色: {missing_characters}"
                })
                suggestions.append(f"确保开头包含角色: {', '.join(required_characters)}")

        # Critical Check 4: 章末钩子设置（出口）
        hook_id = exit_target.get('hook_id', '')
        hook_promise = exit_target.get('hook_promise', '')
        if hook_promise:
            # 简化检查：在最后 20% 寻找悬念标志
            last_fifth = candidate_text[-len(candidate_text) // 5:]
            hook_indicators = ['然而', '但是', '突然', '这时', '就在此时', '忽然', '却', '可是']
            found_indicator = any(ind in last_fifth for ind in hook_indicators)
            if not found_indicator:
                issues.append({
                    "category": "major",
                    "field": "exit_hook",
                    "description": "章末可能缺少明确的钩子"
                })
                suggestions.append("在章节结尾设置悬念钩子")

        # 判断是否需要修订
        critical_issues = [iss for iss in issues if iss["category"] == "critical"]
        requires_revision = len(critical_issues) > 0

        return {
            "pass": len(issues) == 0,
            "issues": issues,
            "requires_revision": requires_revision,
            "revision_suggestions": suggestions
        }

    def _check_location_in_text(self, text: str, location_id: str) -> bool:
        """检查文本中是否包含地点（Task 3.1: 使用配置而非硬编码）"""
        # 从配置加载关键词
        location_keywords = self.config.get('location_keywords', {})
        keywords = location_keywords.get(location_id, [])

        # 如果没有预定义关键词，使用回退策略
        if not keywords:
            fallback = self.config.get('fallback', {})
            if fallback.get('auto_extract_from_id', True):
                # 从 location_id 自动提取关键词
                id_str = location_id
                if fallback.get('strip_loc_prefix', True):
                    id_str = id_str.replace('loc_', '')

                separator = fallback.get('id_separator', '_')
                keywords = id_str.split(separator)

        if not keywords:
            # 完全没有关键词，无法检查
            return False

        # 获取检查范围
        strategy = self.config.get('validation_strategy', {})
        check_portion = strategy.get('location_check_portion', 0.33)

        # P0-4 Fix: 为了避免关键词在边界被截断，我们检查关键词是否
        # *开始于*检查范围内（而不是被范围截断）
        check_length = int(len(text) * check_portion)

        for kw in keywords:
            # 查找关键词在全文中的位置
            pos = text.find(kw)
            if pos != -1 and pos < check_length:
                # 关键词存在，且开始位置在检查范围内
                return True

        return False

    def extract_actual_exit_state(
        self,
        chapter: int,
        final_text: str,
        final_text_hash: str
    ) -> dict:
        """
        从最终正文提取实际出口状态

        Args:
            chapter: 章节号
            final_text: 最终正文
            final_text_hash: 最终正文的 content_hash

        Returns:
            {
                "chapter": int,
                "final_text_hash": str,
                "location_id": str,
                "location_confidence": float,
                "time_state": str,
                "pov": str,
                "characters_present": [str],
                "characters_confidence": float,
                "physical_state": str,
                "emotional_state": str,
                "emotional_confidence": float,
                "unfinished_action": str,
                "unfinished_action_confidence": float,
                "hook_id": str,
                "hook_promise": str,
                "hook_confidence": float,
                "evidence_spans": [{"field": str, "text": str, "confidence": float}],
                "extraction_method": "heuristic_enhanced",
                "overall_confidence": float,
                "extracted_at": str
            }
        """
        from datetime import datetime, timezone

        # 加载契约以获取 planned exit_target
        contract = self._load_contract(chapter)
        planned_exit = contract.get('exit_target', {}) if contract else {}

        # 简化版提取：使用启发式规则从最后 20% 的正文提取
        text_len = len(final_text)
        last_portion = final_text[int(text_len * 0.8):]  # 最后 20%

        # 使用新的置信度方法提取各字段
        location, loc_conf, loc_evidence = self._extract_location_with_confidence(
            last_portion, planned_exit.get('location_id'))

        characters, char_conf, char_evidence = self._extract_characters_with_confidence(
            last_portion, planned_exit.get('characters_present'))

        emotion, emo_conf, emo_evidence = self._extract_emotional_state_with_confidence(
            last_portion)

        unfinished, unfin_conf, unfin_evidence = self._extract_unfinished_action_with_confidence(
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

        if unfin_evidence.get("text"):
            evidence_spans.append({
                "field": "unfinished_action",
                "text": unfin_evidence["text"],
                "confidence": unfin_conf,
                "pattern": unfin_evidence.get("pattern")
            })

        if hook_evidence.get("text"):
            evidence_spans.append({
                "field": "hook_promise",
                "text": hook_evidence["text"],
                "confidence": hook_conf,
                "indicator": hook_evidence.get("indicator")
            })

        # 计算总体置信度（加权平均）
        # 权重: location=0.25, characters=0.25, emotion=0.15, unfinished=0.15, hook=0.2
        overall_confidence = (
            loc_conf * 0.25 +
            char_conf * 0.25 +
            emo_conf * 0.15 +
            unfin_conf * 0.15 +
            hook_conf * 0.2
        )

        actual_exit = {
            "chapter": chapter,
            "final_text_hash": final_text_hash,
            "location_id": location,
            "location_confidence": loc_conf,
            "time_state": self._extract_time_state(last_portion),
            "pov": contract.get('entry_state', {}).get('pov', 'unknown') if contract else 'unknown',
            "characters_present": characters,
            "characters_confidence": char_conf,
            "physical_state": self._extract_physical_state(last_portion),
            "emotional_state": emotion,
            "emotional_confidence": emo_conf,
            "unfinished_action": unfinished,
            "unfinished_action_confidence": unfin_conf,
            "hook_id": planned_exit.get('hook_id', f"hook_{chapter:03d}_extracted"),
            "hook_promise": hook,
            "hook_confidence": hook_conf,
            "evidence_spans": evidence_spans,
            "extraction_method": "heuristic_enhanced",
            "overall_confidence": overall_confidence,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

        return actual_exit

    def _extract_location(self, text: str, planned_location: str = None) -> str:
        """提取地点（启发式，Task 3.1: 使用配置）

        保留此方法用于向后兼容。新代码应使用 _extract_location_with_confidence。
        """
        location, _, _ = self._extract_location_with_confidence(text, planned_location)
        return location

    def _extract_location_with_confidence(self, text: str, planned_location: str = None):
        """提取地点，返回值、置信度和证据

        Returns:
            (location_id, confidence, evidence_dict)

        Confidence levels:
            1.0 - 匹配到配置的关键词
            0.7 - 从计划地点 ID 提取的关键词在文中找到
            0.5 - 使用计划地点作为回退
            0.3 - 返回 loc_unknown
        """
        # 从配置加载地点关键词
        location_keywords = self.config.get('location_keywords', {})

        # 方法 1: 配置关键词匹配（高置信度）
        for loc_id, keywords in location_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    idx = text.find(keyword)
                    evidence_text = text[max(0, idx-20):min(len(text), idx+len(keyword)+20)]
                    return loc_id, 1.0, {"text": evidence_text, "match": keyword}

        # 方法 2: 从计划地点提取关键词（中等置信度）
        if planned_location:
            fallback = self.config.get('fallback', {})
            if fallback.get('auto_extract_from_id', True):
                id_str = planned_location
                if fallback.get('strip_loc_prefix', True):
                    id_str = id_str.replace('loc_', '')
                keywords = id_str.split(fallback.get('id_separator', '_'))
                for kw in keywords:
                    if kw and kw in text:
                        idx = text.find(kw)
                        evidence_text = text[max(0, idx-20):min(len(text), idx+len(kw)+20)]
                        return planned_location, 0.7, {"text": evidence_text, "match": kw}

            # 方法 3: 回退到计划地点（低置信度）
            return planned_location, 0.5, {"text": "", "match": "planned_fallback"}

        # 方法 4: 未知（极低置信度）
        return 'loc_unknown', 0.3, {"text": "", "match": "none"}

    def _extract_time_state(self, text: str) -> str:
        """提取时间状态（启发式）"""
        if '夜幕降临' in text or '天色已晚' in text or '夜' in text[-100:]:
            return 'night'
        elif '黎明' in text or '清晨' in text:
            return 'dawn'
        elif '正午' in text or '中午' in text:
            return 'noon'
        else:
            return 'continuous'

    def _extract_characters_present(self, text: str) -> list:
        """提取在场角色（启发式）

        保留此方法用于向后兼容。新代码应使用 _extract_characters_with_confidence。
        """
        characters, _, _ = self._extract_characters_with_confidence(text)
        return characters

    def _extract_characters_with_confidence(self, text: str, planned_characters: list = None):
        """提取在场人物，返回列表、置信度和证据

        Returns:
            (characters, confidence, evidence_spans)

        Confidence levels:
            0.8 - 找到至少一个角色
            0.4 - 没找到但有计划角色（回退）
            0.2 - 完全未知
        """
        # 简化版：检查常见角色名
        characters = []
        common_names = ['主角', '导师', '段奕尘', '镜见川']
        evidence_spans = []

        for name in common_names:
            if name in text:
                idx = text.find(name)
                evidence_text = text[max(0, idx-20):min(len(text), idx+len(name)+20)]
                characters.append(name)
                evidence_spans.append({"text": evidence_text, "character": name})

        if characters:
            # 找到至少一个角色（中高置信度）
            confidence = 0.8
        elif planned_characters:
            # 没找到但有计划角色（低置信度）
            characters = planned_characters
            confidence = 0.4
        else:
            # 完全未知（极低置信度）
            characters = ['unknown']
            confidence = 0.2

        return characters, confidence, evidence_spans

    def _extract_physical_state(self, text: str) -> str:
        """提取物理状态（启发式）"""
        if '受伤' in text or '流血' in text or '伤口' in text:
            return 'injured'
        elif '疲惫' in text or '筋疲力尽' in text:
            return 'exhausted'
        elif '恢复' in text or '痊愈' in text:
            return 'recovered'
        else:
            return 'normal'

    def _extract_emotional_state(self, text: str) -> str:
        """提取情感状态（启发式）

        保留此方法用于向后兼容。新代码应使用 _extract_emotional_state_with_confidence。
        """
        emotion, _, _ = self._extract_emotional_state_with_confidence(text)
        return emotion

    def _extract_emotional_state_with_confidence(self, text: str):
        """提取情绪状态，返回值、置信度和证据

        Returns:
            (emotion, confidence, evidence_dict)

        Confidence levels:
            0.9 - 找到明确情绪关键词
            0.4 - 未找到，返回 neutral
        """
        emotion_keywords = {
            'angry': ['愤怒', '怒'],
            'fearful': ['恐惧', '害怕'],
            'determined': ['决心', '坚定'],
            'confused': ['困惑', '迷茫'],
            'hopeful': ['希望', '期待', '憧憬'],
            'desperate': ['绝望', '无助'],
            'calm': ['平静', '淡然', '从容'],
            'tense': ['紧张', '焦虑', '不安'],
        }

        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    idx = text.find(keyword)
                    evidence_text = text[max(0, idx-20):min(len(text), idx+len(keyword)+20)]
                    return emotion, 0.9, {"text": evidence_text, "match": keyword}

        # 未找到明确情绪关键词
        return 'neutral', 0.4, {"text": "", "match": "none"}

    def _extract_unfinished_action(self, text: str) -> str:
        """提取未完成动作（启发式）

        保留此方法用于向后兼容。新代码应使用 _extract_unfinished_action_with_confidence。
        """
        action, _, _ = self._extract_unfinished_action_with_confidence(text)
        return action

    def _extract_unfinished_action_with_confidence(self, text: str):
        """提取未完成动作，返回值、置信度和证据

        Returns:
            (action_text, confidence, evidence_dict)

        Confidence levels:
            0.7 - 找到动作意图模式
            0.3 - 未找到
        """
        # 寻找最后的动作意图
        action_patterns = [
            '必须', '需要', '要去', '应该', '打算', '计划'
        ]

        last_sentences = text.split('。')[-5:]  # 最后5句
        for sentence in reversed(last_sentences):
            for pattern in action_patterns:
                if pattern in sentence:
                    return sentence.strip(), 0.7, {"text": sentence.strip(), "pattern": pattern}

        return '未检测到明确的未完成动作', 0.3, {"text": "", "pattern": "none"}

    def _extract_hook_promise(self, text: str) -> str:
        """提取章末钩子承诺（启发式）

        保留此方法用于向后兼容。新代码应使用 _extract_hook_promise_with_confidence。
        """
        hook, _, _ = self._extract_hook_promise_with_confidence(text)
        return hook

    def _extract_hook_promise_with_confidence(self, text: str):
        """提取章末钩子承诺，返回值、置信度和证据

        Returns:
            (hook_text, confidence, evidence_dict)

        Confidence levels:
            0.7 - 找到钩子指示词
            0.4 - 没有指示词，返回最后一段
        """
        # 寻找最后的悬念或预示
        last_paragraph = text.split('\n\n')[-1] if '\n\n' in text else text[-200:]

        hook_indicators = ['然而', '但是', '突然', '这时', '就在此时', '忽然']
        for indicator in hook_indicators:
            if indicator in last_paragraph:
                # 找到指示词后的内容作为钩子
                parts = last_paragraph.split(indicator, 1)
                if len(parts) > 1:
                    hook_text = indicator + parts[1].strip()
                    return hook_text, 0.7, {"text": hook_text, "indicator": indicator}

        # 如果没有明显钩子，返回最后一段（低置信度）
        last_text = last_paragraph.strip()[-100:] if len(last_paragraph) > 100 else last_paragraph.strip()
        return last_text, 0.4, {"text": last_text, "indicator": "last_paragraph"}

    def compare_planned_vs_actual(
        self,
        chapter: int,
        actual_exit: dict
    ) -> dict:
        """
        对比计划出口与实际出口

        Args:
            chapter: 章节号
            actual_exit: 实际出口状态

        Returns:
            {
                "chapter": int,
                "deviations": [
                    {
                        "field": str,
                        "planned": any,
                        "actual": any,
                        "severity": "minor" | "major" | "critical"
                    }
                ],
                "match_score": float
            }
        """
        contract = self._load_contract(chapter)
        if not contract:
            return {
                "chapter": chapter,
                "deviations": [],
                "match_score": 0.0,
                "error": "Contract not found"
            }

        planned_exit = contract.get('exit_target', {})
        deviations = []

        # 对比地点
        if planned_exit.get('location_id') != actual_exit.get('location_id'):
            deviations.append({
                "field": "location_id",
                "planned": planned_exit.get('location_id'),
                "actual": actual_exit.get('location_id'),
                "confidence": actual_exit.get('location_confidence', 0.6),
                "severity": "critical"  # 地点错误是关键偏差
            })

        # 对比人物
        planned_chars = set(planned_exit.get('characters_present', []))
        actual_chars = set(actual_exit.get('characters_present', []))
        if planned_chars != actual_chars:
            missing = planned_chars - actual_chars
            extra = actual_chars - planned_chars
            if missing or extra:
                deviations.append({
                    "field": "characters_present",
                    "planned": list(planned_chars),
                    "actual": list(actual_chars),
                    "missing": list(missing),
                    "extra": list(extra),
                    "confidence": actual_exit.get('characters_confidence', 0.6),
                    "severity": "high" if missing else "minor"
                })

        # 对比钩子承诺（新增）
        planned_hook = planned_exit.get('hook_promise', '')
        actual_hook = actual_exit.get('hook_promise', '')
        if planned_hook and actual_hook and planned_hook != actual_hook:
            deviations.append({
                "field": "hook_promise",
                "planned": planned_hook,
                "actual": actual_hook,
                "confidence": actual_exit.get('hook_confidence', 0.6),
                "severity": "high"  # 钩子承诺偏差重要
            })

        # 对比未完成动作（新增）
        planned_action = planned_exit.get('unfinished_action', '')
        actual_action = actual_exit.get('unfinished_action', '')
        if planned_action and actual_action and planned_action != actual_action:
            deviations.append({
                "field": "unfinished_action",
                "planned": planned_action,
                "actual": actual_action,
                "confidence": actual_exit.get('unfinished_action_confidence', 0.6),
                "severity": "medium"
            })

        # 对比时间状态（新增）
        planned_time = planned_exit.get('time_state', '')
        actual_time = actual_exit.get('time_state', '')
        if planned_time and actual_time and planned_time != actual_time:
            deviations.append({
                "field": "time_state",
                "planned": planned_time,
                "actual": actual_time,
                "severity": "minor"
            })

        # 对比情绪状态（新增）
        planned_emotion = planned_exit.get('emotional_state', '')
        actual_emotion = actual_exit.get('emotional_state', '')
        if planned_emotion and actual_emotion and planned_emotion != actual_emotion:
            deviations.append({
                "field": "emotional_state",
                "planned": planned_emotion,
                "actual": actual_emotion,
                "confidence": actual_exit.get('emotional_confidence', 0.6),
                "severity": "minor"
            })

        # 对比身体状态（新增）
        planned_physical = planned_exit.get('physical_state', '')
        actual_physical = actual_exit.get('physical_state', '')
        if planned_physical and actual_physical and planned_physical != actual_physical:
            deviations.append({
                "field": "physical_state",
                "planned": planned_physical,
                "actual": actual_physical,
                "severity": "minor"
            })

        # 统计不同严重级别的偏差
        critical_count = len([d for d in deviations if d.get("severity") == "critical"])
        high_count = len([d for d in deviations if d.get("severity") == "high"])
        medium_count = len([d for d in deviations if d.get("severity") == "medium"])
        minor_count = len([d for d in deviations if d.get("severity") == "minor"])

        # 计算匹配分数（扩展到 8 个字段）
        total_checks = 8  # location, characters, hook, action, time, emotion, physical, pov
        match_score = (total_checks - len(deviations)) / total_checks if total_checks > 0 else 0.0

        # P2: 严格模式检查
        strict_mode_result = {}
        if self.strict_mode:
            overall_conf = actual_exit.get("overall_confidence", 0.6)
            confidence_threshold = self.strict_config.get("confidence_threshold", 0.7)

            # 检查 1: 关键偏差阻断
            if self.strict_config.get("block_critical_deviations", True) and critical_count > 0:
                strict_mode_result["status"] = ChapterStatus.CONTRACT_INVALID.value
                strict_mode_result["reason"] = f"Critical deviations detected: {critical_count}"
                strict_mode_result["blocked"] = True

            # 检查 2: 低置信度阻断
            elif self.strict_config.get("block_low_confidence", True) and overall_conf < confidence_threshold:
                strict_mode_result["status"] = ChapterStatus.REQUIRES_HUMAN_REVIEW.value
                strict_mode_result["reason"] = f"Low confidence extraction: {overall_conf:.2f} < {confidence_threshold}"
                strict_mode_result["blocked"] = True

            # 检查 3: 高级别偏差警告
            elif high_count > 0:
                strict_mode_result["status"] = ChapterStatus.CONTRACT_WARNING.value
                strict_mode_result["reason"] = f"High-severity deviations detected: {high_count}"
                strict_mode_result["blocked"] = False

            # 检查 4: 通过
            else:
                strict_mode_result["status"] = ChapterStatus.PRODUCED.value
                strict_mode_result["reason"] = "All checks passed"
                strict_mode_result["blocked"] = False

        result = {
            "chapter": chapter,
            "deviations": deviations,
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "minor_count": minor_count,
            "total_deviations": len(deviations),
            "match_score": match_score,
            "overall_alignment": match_score  # 别名
        }

        # 添加严格模式结果
        if self.strict_mode:
            result["strict_mode"] = strict_mode_result

        return result
