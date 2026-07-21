import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Edge, Node } from "@xyflow/react";

import { api } from "../api";
import RailwayNode from "../components/topology/RailwayNode";
import { getLayoutedElements } from "../components/topology/layout";

export interface Topology {
    nodes: {
        id: number;
        name: string;
        vendor: string;
        type: string;
        ip: string;
    }[];

    edges: {
        source: number;
        target: number;
        label: string;
    }[];
}

export function useTopology() {

    const topology = useQuery({
        queryKey: ["topology"],
        queryFn: () =>
            api.get<Topology>("/topology")
                .then(r => r.data),
    });

    const graph = useMemo(() => {

        const nodes: Node[] =
            (topology.data?.nodes ?? []).map((device) => ({
                id: String(device.id),

                position: { x: 0, y: 0 },

                data: {
                    label: (
                        <RailwayNode
                            name={device.name}
                            vendor={device.vendor}
                            ip={device.ip}
                            deviceType={device.type}
                            status="online"
                        />
                    ),
                },

                style: {
                    border: "none",
                    background: "transparent",
                },
            }));

        const edges: Edge[] =
            (topology.data?.edges ?? []).map((edge, index) => ({
                id: `edge-${index}`,
                source: String(edge.source),
                target: String(edge.target),
                label: edge.label,
            }));

        return getLayoutedElements(nodes, edges);

    }, [topology.data]);

    return {

        ...topology,

        nodes: graph.nodes,

        edges: graph.edges,

    };
}