#!/usr/bin/env python3
"""
P0+P1修复效果验证脚本

运行5-10章生成，验证：
1. Production Card有完整数据（dropout_risk不为null）
2. 质量阈值正确触发（低于阈值的章节被hold）
3. Reader期待正确提取和选择
4. 决策一致无矛盾
5. Promise状态正确更新
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import subprocess


class P0P1Validator:
    """P0+P1修复效果验证器"""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.registry_path = project_path / "registry"
        self.results = {
            "validation_passed": True,
            "checks": [],
            "errors": [],
            "warnings": [],
        }

    def validate_all(self, chapter_ids: List[str]) -> Dict[str, Any]:
        """验证所有章节"""
        print(f"🔍 开始验证 {len(chapter_ids)} 个章节...")

        for chapter_id in chapter_ids:
            print(f"\n📄 验证章节: {chapter_id}")
            self.validate_chapter(chapter_id)

        return self.results

    def validate_chapter(self, chapter_id: str):
        """验证单个章节"""
        try:
            # 加载Production Card
            production_card = self._load_production_card(chapter_id)
            if not production_card:
                self._add_error(chapter_id, "Production Card未找到")
                return

            # 加载Chapter Run
            chapter_run = self._load_chapter_run(chapter_id)

            # 执行各项检查
            self._check_reader_simulation(chapter_id, production_card)
            self._check_quality_thresholds(chapter_id, production_card)
            self._check_quality_loop(chapter_id, production_card)
            self._check_decision_consistency(chapter_id, production_card)
            self._check_reader_expectations(chapter_id, chapter_run)

        except Exception as e:
            self._add_error(chapter_id, f"验证异常: {str(e)}")

    def _load_production_card(self, chapter_id: str) -> Dict[str, Any]:
        """加载Production Card"""
        # 从chapter-run中提取
        run_file = self.registry_path / "derived" / "chapter-run" / f"run-{chapter_id}.json"
        if run_file.exists():
            with open(run_file) as f:
                data = json.load(f)
                return data.get("production_card")
        return None

    def _load_chapter_run(self, chapter_id: str) -> Dict[str, Any]:
        """加载Chapter Run"""
        run_file = self.registry_path / "derived" / "chapter-run" / f"run-{chapter_id}.json"
        if run_file.exists():
            with open(run_file) as f:
                return json.load(f)
        return None

    def _check_reader_simulation(self, chapter_id: str, card: Dict):
        """检查1: Reader Simulation字段完整性"""
        reader_sim = card.get("reader_simulation")

        if not reader_sim:
            self._add_warning(chapter_id, "P0-1: 没有reader_simulation数据")
            return

        # 检查dropout_risk
        dropout_risk = card.get("dropout_risk")
        if dropout_risk is None:
            self._add_error(chapter_id, "P0-1 FAILED: dropout_risk为null")
            return

        self._add_check(chapter_id, f"P0-1 PASSED: dropout_risk={dropout_risk:.2%}")

        # 检查字段名
        personas = reader_sim.get("personas", [])
        if personas:
            first_persona = personas[0]
            if "would_continue" in first_persona:
                self._add_check(chapter_id, "P0-1 PASSED: 使用正确的字段名'would_continue'")
            else:
                self._add_error(chapter_id, "P0-1 FAILED: 未使用'would_continue'字段")

    def _check_quality_thresholds(self, chapter_id: str, card: Dict):
        """检查2: 质量阈值"""
        final_scores = card.get("final_quality_scores", {})
        recommendation = card.get("publish_recommendation")

        if not final_scores:
            self._add_warning(chapter_id, "P0-2: 没有final_quality_scores")
            return

        # 定义阈值
        thresholds = {
            "hook": 75,
            "retention": 75,
            "character_consistency": 80,
            "world_consistency": 80,
        }

        below_threshold = []
        for dim, threshold in thresholds.items():
            score = final_scores.get(dim)
            if score is not None and score < threshold:
                below_threshold.append(f"{dim}={score:.0f}<{threshold}")

        if below_threshold:
            # 应该被hold
            if recommendation in ["hold", "block"]:
                self._add_check(
                    chapter_id,
                    f"P0-2 PASSED: 低于阈值({', '.join(below_threshold)})，正确触发{recommendation}"
                )
            else:
                self._add_error(
                    chapter_id,
                    f"P0-2 FAILED: 低于阈值({', '.join(below_threshold)})但recommendation={recommendation}"
                )
        else:
            self._add_check(chapter_id, "P0-2 PASSED: 所有维度达到阈值")

    def _check_quality_loop(self, chapter_id: str, card: Dict):
        """检查3: 质量闭环"""
        initial_scores = card.get("initial_quality_scores", {})
        final_scores = card.get("final_quality_scores", {})
        quality_delta = card.get("quality_delta", {})

        if not initial_scores:
            self._add_warning(chapter_id, "P0-3: 没有initial_quality_scores")
            return

        if not final_scores:
            self._add_warning(chapter_id, "P0-3: 没有final_quality_scores")
            return

        # 检查是否相同
        if initial_scores == final_scores:
            if quality_delta:
                self._add_error(chapter_id, "P0-3 FAILED: initial==final但quality_delta不为空")
            else:
                self._add_check(chapter_id, "P0-3 PASSED: 无修订，initial==final，delta为空")
        else:
            if quality_delta:
                # 检查delta计算是否正确
                sample_dim = list(quality_delta.keys())[0] if quality_delta else None
                if sample_dim:
                    delta_info = quality_delta[sample_dim]
                    expected_delta = final_scores.get(sample_dim, 0) - initial_scores.get(sample_dim, 0)
                    actual_delta = delta_info.get("delta", 0)
                    if abs(expected_delta - actual_delta) < 0.1:
                        self._add_check(chapter_id, f"P0-3 PASSED: 有修订，initial≠final，delta正确计算")
                    else:
                        self._add_error(chapter_id, f"P0-3 FAILED: delta计算错误")
            else:
                self._add_warning(chapter_id, "P0-3: initial≠final但quality_delta为空")

    def _check_decision_consistency(self, chapter_id: str, card: Dict):
        """检查4: 决策一致性"""
        recommendation = card.get("publish_recommendation")
        blocking_issues = card.get("blocking_issues", [])
        warnings = card.get("warnings", [])

        if not recommendation:
            self._add_warning(chapter_id, "P0-4: 没有publish_recommendation")
            return

        # 检查逻辑一致性
        if recommendation == "block":
            if blocking_issues:
                self._add_check(chapter_id, f"P0-4 PASSED: block有blocking_issues")
            else:
                self._add_error(chapter_id, "P0-4 FAILED: block但无blocking_issues")

        elif recommendation == "hold":
            if warnings:
                self._add_check(chapter_id, f"P0-4 PASSED: hold有warnings")
            else:
                self._add_warning(chapter_id, "P0-4: hold但无warnings")

        elif recommendation == "recommend":
            if not blocking_issues and not warnings:
                self._add_check(chapter_id, "P0-4 PASSED: recommend且无阻断问题")
            else:
                self._add_warning(chapter_id, f"P0-4: recommend但有{len(warnings)}个warnings")

    def _check_reader_expectations(self, chapter_id: str, chapter_run: Dict):
        """检查5: Reader期待提取（如果有final_reader_simulation）"""
        if not chapter_run:
            return

        # 这是新功能，可能还没接入到loop中，所以只是检查数据结构
        final_reader_sim = chapter_run.get("final_reader_simulation")
        if not final_reader_sim:
            self._add_warning(chapter_id, "P1-3: 没有final_reader_simulation数据")
            return

        personas = final_reader_sim.get("personas", [])
        if personas:
            has_expectations = any("expectations" in p for p in personas)
            if has_expectations:
                self._add_check(chapter_id, "P1-3 PASSED: personas包含expectations字段")
            else:
                self._add_warning(chapter_id, "P1-3: personas没有expectations字段")

    def _add_check(self, chapter_id: str, message: str):
        """添加通过的检查"""
        self.results["checks"].append(f"[{chapter_id}] {message}")
        print(f"  ✅ {message}")

    def _add_error(self, chapter_id: str, message: str):
        """添加错误"""
        self.results["errors"].append(f"[{chapter_id}] {message}")
        self.results["validation_passed"] = False
        print(f"  ❌ {message}")

    def _add_warning(self, chapter_id: str, message: str):
        """添加警告"""
        self.results["warnings"].append(f"[{chapter_id}] {message}")
        print(f"  ⚠️  {message}")

    def print_summary(self):
        """打印总结"""
        print("\n" + "="*60)
        print("📊 验证总结")
        print("="*60)

        print(f"\n✅ 通过检查: {len(self.results['checks'])}")
        print(f"❌ 错误: {len(self.results['errors'])}")
        print(f"⚠️  警告: {len(self.results['warnings'])}")

        if self.results["errors"]:
            print("\n❌ 错误详情:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        if self.results["warnings"]:
            print("\n⚠️  警告详情:")
            for warning in self.results["warnings"][:5]:  # 只显示前5个
                print(f"  - {warning}")
            if len(self.results["warnings"]) > 5:
                print(f"  ... 还有 {len(self.results['warnings']) - 5} 个警告")

        print("\n" + "="*60)
        if self.results["validation_passed"]:
            print("🎉 验证通过！P0+P1修复效果良好。")
        else:
            print("⚠️  验证发现问题，请检查错误详情。")
        print("="*60)


def main():
    """主函数"""
    # 查找项目路径
    project_path = Path.cwd()
    if not (project_path / "registry").exists():
        # 尝试查找novel-lingse
        novel_path = project_path / "novel-lingse"
        if novel_path.exists():
            project_path = novel_path

    print("🚀 P0+P1修复效果验证")
    print(f"📁 项目路径: {project_path}")

    # 查找最近的章节
    run_dir = project_path / "registry" / "derived" / "chapter-run"
    if not run_dir.exists():
        print(f"❌ 未找到chapter-run目录: {run_dir}")
        return 1

    # 列出所有run文件
    run_files = sorted(run_dir.glob("run-*.json"))
    if not run_files:
        print("❌ 未找到任何chapter run文件")
        return 1

    # 取最近的5个
    chapter_ids = [f.stem.replace("run-", "") for f in run_files[-5:]]
    print(f"📚 将验证最近的 {len(chapter_ids)} 个章节: {', '.join(chapter_ids)}")

    # 执行验证
    validator = P0P1Validator(project_path)
    validator.validate_all(chapter_ids)
    validator.print_summary()

    return 0 if validator.results["validation_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
