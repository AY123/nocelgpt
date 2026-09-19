"""
Tests for P0-3: Wire Governance Modules

Validates that the three governance modules (PromiseDebtTracker,
CharacterArcValidator, WorldConsistencyChecker) are called during
production and their findings are recorded in Production Cards.
"""
import pytest
from pathlib import Path


class TestGovernanceModulesWired:
    """Test that governance modules are wired into the production loop"""

    def test_promise_debt_tracker_called_in_loop(self):
        """P0-3: PromiseDebtTracker should be imported and called in loop.py"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Check import
        assert "from ..promise_debt_tracker import PromiseDebtTracker" in code, \
            "PromiseDebtTracker should be imported in loop.py"

        # Check instantiation
        assert "tracker = PromiseDebtTracker()" in code, \
            "PromiseDebtTracker should be instantiated"

        # Check method call
        assert "tracker.analyze_debt(" in code, \
            "analyze_debt() should be called"

    def test_character_arc_validator_called_in_loop(self):
        """P0-3: CharacterArcValidator should be imported and called in loop.py"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Check import
        assert "from ..character_arc_validator import CharacterArcValidator" in code, \
            "CharacterArcValidator should be imported in loop.py"

        # Check instantiation
        assert "validator = CharacterArcValidator()" in code, \
            "CharacterArcValidator should be instantiated"

        # Check method call
        assert "validator.validate_arc(" in code, \
            "validate_arc() should be called"

    def test_world_consistency_checker_called_in_loop(self):
        """P0-3: WorldConsistencyChecker should be imported and called in loop.py"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Check import
        assert "from ..world_consistency_checker import WorldConsistencyChecker" in code, \
            "WorldConsistencyChecker should be imported in loop.py"

        # Check instantiation
        assert "checker = WorldConsistencyChecker()" in code, \
            "WorldConsistencyChecker should be instantiated"

        # Check method call
        assert "checker.check_consistency(" in code, \
            "check_consistency() should be called"

    def test_governance_reports_structure(self):
        """P0-3: governance_reports should have all three module outputs"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Check governance_reports dict exists
        assert 'governance_reports = {' in code, \
            "governance_reports dict should be initialized"

        # Check all three keys
        assert '"promise_debt": None' in code, \
            "governance_reports should have promise_debt key"
        assert '"character_arc": None' in code, \
            "governance_reports should have character_arc key"
        assert '"world_consistency": None' in code, \
            "governance_reports should have world_consistency key"

    def test_governance_reports_assigned_to_production_card(self):
        """P0-3: governance_reports should be passed to ProductionCard"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Check governance_reports is passed to ProductionCard
        assert "governance_reports=governance_reports" in code, \
            "governance_reports should be passed to ProductionCard"


class TestProductionCardGovernanceField:
    """Test that ProductionCard has governance_reports field"""

    def test_production_card_has_governance_field(self):
        """P0-3: ProductionCard should have governance_reports field"""
        from runtime.production_card import ProductionCard
        from dataclasses import fields

        field_names = [f.name for f in fields(ProductionCard)]
        assert "governance_reports" in field_names, \
            "ProductionCard should have governance_reports field"

    def test_production_card_governance_field_optional(self):
        """P0-3: governance_reports field should be Optional"""
        card_file = Path(__file__).parent.parent / "runtime" / "production_card.py"
        code = card_file.read_text(encoding="utf-8")

        # Check field definition includes Optional
        assert "governance_reports: Optional[Dict]" in code, \
            "governance_reports should be Optional[Dict]"


class TestGovernanceErrorHandling:
    """Test that governance module errors are handled gracefully (ADR-003)"""

    def test_promise_debt_has_exception_handler(self):
        """P0-3: Promise debt tracking should have exception handler"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Find the promise debt section
        lines = code.split('\n')
        in_promise_section = False
        has_try = False
        has_except = False

        for line in lines:
            if "PromiseDebtTracker()" in line:
                in_promise_section = True
            if in_promise_section:
                if "try:" in line:
                    has_try = True
                if "except" in line and "debt" in line.lower():
                    has_except = True
                if has_try and has_except:
                    break
                if "CharacterArcValidator" in line:
                    break

        assert has_try and has_except, \
            "Promise debt tracking should have try/except for graceful degradation"

    def test_character_arc_has_exception_handler(self):
        """P0-3: Character arc validation should have exception handler"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Character arc section should have try/except
        lines = code.split('\n')
        in_arc_section = False
        has_try = False
        has_except = False

        for line in lines:
            if "CharacterArcValidator()" in line:
                in_arc_section = True
            if in_arc_section:
                if "try:" in line:
                    has_try = True
                if "except" in line and "arc" in line.lower():
                    has_except = True
                if has_try and has_except:
                    break
                if "WorldConsistencyChecker" in line:
                    break

        assert has_try and has_except, \
            "Character arc validation should have try/except for graceful degradation"

    def test_world_consistency_has_exception_handler(self):
        """P0-3: World consistency check should have exception handler"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # World consistency section should have try/except
        lines = code.split('\n')
        in_consistency_section = False
        has_try = False
        has_except = False

        for line in lines:
            if "WorldConsistencyChecker()" in line:
                in_consistency_section = True
            if in_consistency_section:
                if "try:" in line:
                    has_try = True
                if "except" in line and "consistency" in line.lower():
                    has_except = True
                if has_try and has_except:
                    break

        assert has_try and has_except, \
            "World consistency check should have try/except for graceful degradation"


class TestGovernanceLogging:
    """Test that critical governance findings are logged"""

    def test_critical_promise_debt_logged(self):
        """P0-3: Critical promise debt should be logged"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Should log when critical debts detected
        assert "CRITICAL promise debt" in code, \
            "Critical promise debt should be logged"
        assert "debt_report.critical_debts" in code, \
            "Should check for critical_debts"

    def test_critical_arc_issues_logged(self):
        """P0-3: Critical character arc issues should be logged"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Should log when critical arc issues detected
        assert "Character arc issues" in code, \
            "Character arc issues should be logged"

    def test_critical_inconsistencies_logged(self):
        """P0-3: Critical world inconsistencies should be logged"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Should log when critical inconsistencies detected
        assert "CRITICAL world inconsistencies" in code, \
            "Critical world inconsistencies should be logged"
        assert "critical_inconsistencies" in code, \
            "Should check for critical_inconsistencies"


class TestGovernanceAdvisoryOnly:
    """Test that governance checks are advisory only (ADR-003: never gate)"""

    def test_governance_does_not_gate_production(self):
        """P0-3: Governance checks should never block chapter production"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Find governance section
        lines = code.split('\n')
        governance_section = []
        in_section = False

        for line in lines:
            if "P0-3: Governance Module Checks" in line:
                in_section = True
            if in_section:
                governance_section.append(line)
            if "Production Card: unified final-draft quality card" in line:
                break

        section_text = '\n'.join(governance_section)

        # Should NOT have any gating logic (return, continue, raise)
        # in the governance section outside of exception handlers
        for line in governance_section:
            if "return" in line or "continue" in line:
                # Should only appear in exception handlers or comments
                assert "except" in section_text[max(0, section_text.find(line) - 200):section_text.find(line)], \
                    f"Governance should not gate (found '{line.strip()}')"


class TestGovernanceReportStructure:
    """Test the structure of governance reports"""

    def test_promise_debt_report_structure(self):
        """P0-3: Promise debt report should have expected fields"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Check required fields
        assert '"total_pending":' in code, \
            "Promise debt report should include total_pending"
        assert '"critical_count":' in code, \
            "Promise debt report should include critical_count"
        assert '"recommendations":' in code, \
            "Promise debt report should include recommendations"
        assert '"next_chapter_suggestions":' in code, \
            "Promise debt report should include next_chapter_suggestions"

    def test_character_arc_report_structure(self):
        """P0-3: Character arc report should have expected fields"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Check required fields
        assert '"validated_characters":' in code, \
            "Character arc report should include validated_characters"
        assert '"characters_with_issues":' in code, \
            "Character arc report should include characters_with_issues"
        assert '"arc_health_score":' in code, \
            "Character arc report should include arc_health_score"

    def test_world_consistency_report_structure(self):
        """P0-3: World consistency report should have expected fields"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Check required fields
        assert '"total_rules":' in code, \
            "World consistency report should include total_rules"
        assert '"total_inconsistencies":' in code, \
            "World consistency report should include total_inconsistencies"
        assert '"consistency_score":' in code, \
            "World consistency report should include consistency_score"


class TestGovernancePlacement:
    """Test that governance checks are at the right stage"""

    def test_governance_after_promise_delivery(self):
        """P0-3: Governance checks should run after promise delivery check"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Find positions
        promise_delivery_pos = code.find("# --- Promise Delivery Check")
        governance_pos = code.find("# --- P0-3: Governance Module Checks")

        assert promise_delivery_pos > 0, "Promise delivery section should exist"
        assert governance_pos > 0, "Governance section should exist"
        assert governance_pos > promise_delivery_pos, \
            "Governance checks should run after promise delivery"

    def test_governance_before_production_card(self):
        """P0-3: Governance checks should run before Production Card"""
        loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
        code = loop_file.read_text(encoding="utf-8")

        # Find positions
        governance_pos = code.find("# --- P0-3: Governance Module Checks")
        production_card_pos = code.find("# --- Production Card: unified final-draft quality card")

        assert governance_pos > 0, "Governance section should exist"
        assert production_card_pos > 0, "Production Card section should exist"
        assert governance_pos < production_card_pos, \
            "Governance checks should run before Production Card"
