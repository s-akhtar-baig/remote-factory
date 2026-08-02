"""Tests for the simulate workflow definition."""

from __future__ import annotations

from factory.models import ProjectState
from factory.workflow.definitions import register_all, simulate_workflow
from factory.workflow.primitives import (
    AgentNode,
    AgentRole,
    GateNode,
    VerdictType,
)


class TestSimulateWorkflowValidates:
    """Verify the simulate workflow graph passes structural validation."""

    def test_graph_validates(self) -> None:
        """Graph has no structural issues."""
        wf = simulate_workflow()
        issues = wf.validate_graph()
        assert issues == [], f"Validation issues: {issues}"

    def test_node_count(self) -> None:
        """Exactly 10 nodes: 5 agents + 4 gates + 1 archivist."""
        wf = simulate_workflow()
        assert len(wf.nodes) == 10

    def test_edge_count(self) -> None:
        """10 edges: 8 unconditional/PROCEED + 1 RELOOP + 1 PROCEED from gate_verify."""
        wf = simulate_workflow()
        assert len(wf.edges) == 10

    def test_start_node(self) -> None:
        wf = simulate_workflow()
        assert wf.start_node == "analyze_query"

    def test_terminal(self) -> None:
        wf = simulate_workflow()
        assert wf.terminal is True

    def test_name(self) -> None:
        wf = simulate_workflow()
        assert wf.name == "simulate"


class TestSimulateSkillExport:
    """Verify SKILL.md can be generated from the workflow."""

    def test_skill_export(self) -> None:
        from factory.workflow.skill_export import workflow_to_skill_md
        wf = simulate_workflow()
        skill_md = workflow_to_skill_md(wf)
        assert "analyze_query" in skill_md
        assert "snapshot_cluster" in skill_md
        assert "provision_cluster" in skill_md
        assert "apply_manifests" in skill_md
        assert "verify_cluster" in skill_md
        assert "factory agent strategist" in skill_md
        assert "factory agent builder" in skill_md
        assert "factory agent health_checker" in skill_md
        assert "factory agent archivist" in skill_md


class TestSimulateTrigger:
    """Verify the trigger function activates correctly."""

    def test_trigger_fires_on_simulate_mode(self) -> None:
        wf = simulate_workflow()
        assert wf.trigger is not None
        assert wf.trigger(ProjectState.HAS_FACTORY, {"mode": "simulate"}) is True

    def test_trigger_fires_regardless_of_state(self) -> None:
        """Simulate mode works on any project state."""
        wf = simulate_workflow()
        assert wf.trigger is not None
        assert wf.trigger(ProjectState.NO_REPO, {"mode": "simulate"}) is True
        assert wf.trigger(ProjectState.NO_FACTORY, {"mode": "simulate"}) is True

    def test_trigger_does_not_fire_on_other_modes(self) -> None:
        wf = simulate_workflow()
        assert wf.trigger is not None
        assert wf.trigger(ProjectState.HAS_FACTORY, {"mode": "improve"}) is False
        assert wf.trigger(ProjectState.HAS_FACTORY, {}) is False


class TestSimulateRegistration:
    """Verify the workflow is registered in register_all()."""

    def test_registered(self) -> None:
        workflows = register_all()
        assert "simulate" in workflows

    def test_registered_workflow_matches(self) -> None:
        workflows = register_all()
        wf = workflows["simulate"]
        assert wf.name == "simulate"
        assert wf.terminal is True
        assert wf.start_node == "analyze_query"


class TestSimulateNodeDetails:
    """Verify individual node configurations."""

    def test_analyze_query_is_strategist(self) -> None:
        wf = simulate_workflow()
        node = wf.nodes["analyze_query"]
        assert isinstance(node, AgentNode)
        assert node.role == AgentRole.STRATEGIST

    def test_snapshot_cluster_is_builder(self) -> None:
        wf = simulate_workflow()
        node = wf.nodes["snapshot_cluster"]
        assert isinstance(node, AgentNode)
        assert node.role == AgentRole.BUILDER

    def test_provision_cluster_is_builder(self) -> None:
        wf = simulate_workflow()
        node = wf.nodes["provision_cluster"]
        assert isinstance(node, AgentNode)
        assert node.role == AgentRole.BUILDER

    def test_apply_manifests_is_builder(self) -> None:
        wf = simulate_workflow()
        node = wf.nodes["apply_manifests"]
        assert isinstance(node, AgentNode)
        assert node.role == AgentRole.BUILDER

    def test_verify_cluster_is_health_checker(self) -> None:
        wf = simulate_workflow()
        node = wf.nodes["verify_cluster"]
        assert isinstance(node, AgentNode)
        assert node.role == AgentRole.HEALTH_CHECKER

    def test_archivist_is_haiku_nonblocking(self) -> None:
        wf = simulate_workflow()
        node = wf.nodes["archivist"]
        assert isinstance(node, AgentNode)
        assert node.role == AgentRole.ARCHIVIST
        assert node.model == "haiku"
        assert node.blocking is False

    def test_gate_analysis_is_user(self) -> None:
        wf = simulate_workflow()
        node = wf.nodes["gate_analysis"]
        assert isinstance(node, GateNode)
        assert node.evaluator_type == "user"

    def test_gate_snapshot_is_fn(self) -> None:
        wf = simulate_workflow()
        node = wf.nodes["gate_snapshot"]
        assert isinstance(node, GateNode)
        assert node.evaluator_type == "fn"

    def test_gate_provision_is_fn(self) -> None:
        wf = simulate_workflow()
        node = wf.nodes["gate_provision"]
        assert isinstance(node, GateNode)
        assert node.evaluator_type == "fn"

    def test_gate_verify_is_fn(self) -> None:
        wf = simulate_workflow()
        node = wf.nodes["gate_verify"]
        assert isinstance(node, GateNode)
        assert node.evaluator_type == "fn"

    def test_reloop_edge_exists(self) -> None:
        """gate_analysis has a RELOOP edge back to analyze_query."""
        wf = simulate_workflow()
        reloop_edges = [
            e for e in wf.edges
            if e.source == "gate_analysis"
            and e.target == "analyze_query"
            and e.condition == VerdictType.RELOOP
        ]
        assert len(reloop_edges) == 1


class TestSimulateMicroshiftPort:
    """Verify microshift port is configurable, not hardcoded."""

    def test_provision_cluster_no_hardcoded_port_mapping(self) -> None:
        """provision_cluster prompt must NOT contain literal -p 6443:6443."""
        wf = simulate_workflow()
        node = wf.nodes["provision_cluster"]
        assert isinstance(node, AgentNode)
        assert "-p 6443:6443" not in node.prompt_template

    def test_provision_cluster_reads_port_from_analysis(self) -> None:
        """provision_cluster prompt instructs reading microshift_port from analysis.json."""
        wf = simulate_workflow()
        node = wf.nodes["provision_cluster"]
        assert isinstance(node, AgentNode)
        assert "microshift_port" in node.prompt_template
        assert "analysis.json" in node.prompt_template

    def test_provision_cluster_variable_host_fixed_container_port(self) -> None:
        """Port mapping uses -p <microshift_port>:6443 — variable host, fixed container."""
        wf = simulate_workflow()
        node = wf.nodes["provision_cluster"]
        assert isinstance(node, AgentNode)
        assert "<microshift_port>:6443" in node.prompt_template

    def test_analyze_query_includes_microshift_port_in_schema(self) -> None:
        """analysis.json schema includes microshift_port field."""
        wf = simulate_workflow()
        node = wf.nodes["analyze_query"]
        assert isinstance(node, AgentNode)
        assert "microshift_port" in node.prompt_template

    def test_provision_cluster_patches_kubeconfig(self) -> None:
        """provision_cluster prompt includes kubeconfig server URL patching."""
        wf = simulate_workflow()
        node = wf.nodes["provision_cluster"]
        assert isinstance(node, AgentNode)
        assert "sed" in node.prompt_template
        assert "ephemeral-kubeconfig" in node.prompt_template


class TestSimulateDataFlow:
    """Verify reads/writes declarations for data flow validation."""

    def test_analysis_written_before_read(self) -> None:
        """analysis.json is written by analyze_query, read by gate_analysis."""
        wf = simulate_workflow()
        assert ".factory/simulate/analysis.json" in wf.nodes["analyze_query"].writes
        assert ".factory/simulate/analysis.json" in wf.nodes["gate_analysis"].reads

    def test_snapshot_report_written_before_read(self) -> None:
        wf = simulate_workflow()
        assert ".factory/simulate/snapshot-report.md" in wf.nodes["snapshot_cluster"].writes
        assert ".factory/simulate/snapshot-report.md" in wf.nodes["gate_snapshot"].reads

    def test_provision_report_written_before_read(self) -> None:
        wf = simulate_workflow()
        assert ".factory/simulate/provision-report.md" in wf.nodes["provision_cluster"].writes
        assert ".factory/simulate/provision-report.md" in wf.nodes["gate_provision"].reads

    def test_apply_report_written_before_read(self) -> None:
        wf = simulate_workflow()
        assert ".factory/simulate/apply-report.md" in wf.nodes["apply_manifests"].writes
        assert ".factory/simulate/apply-report.md" in wf.nodes["verify_cluster"].reads

    def test_verify_report_written_before_read(self) -> None:
        wf = simulate_workflow()
        assert ".factory/simulate/verify-report.md" in wf.nodes["verify_cluster"].writes
        assert ".factory/simulate/verify-report.md" in wf.nodes["gate_verify"].reads
