import dagre from "@dagrejs/dagre";
import { Node, Edge } from "@xyflow/react";

const nodeWidth = 230;
const nodeHeight = 120;

export function getLayoutedElements(
    nodes: Node[],
    edges: Edge[],
    direction: "TB" | "LR" = "TB"
) {
    const graph = new dagre.graphlib.Graph();

    graph.setDefaultEdgeLabel(() => ({}));

    graph.setGraph({
        rankdir: direction,
        ranksep: 120,
        nodesep: 80,
    });

    nodes.forEach((node) => {
        graph.setNode(node.id, {
            width: nodeWidth,
            height: nodeHeight,
        });
    });

    edges.forEach((edge) => {
        graph.setEdge(edge.source, edge.target);
    });

    dagre.layout(graph);

    const layoutedNodes = nodes.map((node) => {
        const position = graph.node(node.id);

        return {
            ...node,
            position: {
                x: position.x - nodeWidth / 2,
                y: position.y - nodeHeight / 2,
            },
        };
    });

    return {
        nodes: layoutedNodes,
        edges,
    };
}