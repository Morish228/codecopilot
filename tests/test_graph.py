from coding_assistant.runtime.graph import build_agent_graph


def test_graph_compiles():
    graph = build_agent_graph()
    compiled = graph.compile()
    assert compiled is not None
