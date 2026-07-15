import { Alert, Box, Card, CardContent, Typography } from "@mui/material";
import { Background, Controls, Edge, MiniMap, Node, ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import RailwayNode from "../components/topology/RailwayNode";

type Topology = { nodes: { id: number; name: string; vendor: string; type: string; ip: string }[]; edges: { source: number; target: number; label: string }[] };
export default function TopologyPage() { const topology = useQuery({ queryKey: ["topology"], 
    queryFn: () => api.get<Topology>("/topology").then((r) => r.data) }); 
    const nodes: Node[] = (topology.data?.nodes ?? []).map((item, index) => ({ 
        id: String(item.id), 
        position: { x: 80 + (index % 4) * 220, y: 90 + Math.floor(index / 4) * 150 }, 
        data: {
            label: (
                <RailwayNode
                    name={item.name}
                    vendor={item.vendor}
                    ip={item.ip}
                    deviceType={item.type}
                    status="online"
                />
            ),},
        style: { border: "1px solid #1976d2", borderRadius: 8, padding: 10, background: "#111c2e" } })); 
    const edges: Edge[] = (topology.data?.edges ?? []).map((item, index) => ({ 
        id: `edge-${index}`, 
        source: String(item.source), 
        target: String(item.target), label: item.label, animated: false })); 
        return <><Typography variant="h4" gutterBottom>Network Topology</Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>
            LLDP-derived relationships from the latest device polling.
        </Typography>{topology.isError && 
        <Alert severity="warning">Topology data is unavailable until devices are polled and report LLDP neighbors.
        </Alert>}
        <Card><CardContent sx={{ height: 620 }}>
            <ReactFlow nodes={nodes} edges={edges} fitView>
                <Background /><Controls /><MiniMap />
                </ReactFlow></CardContent></Card></>; }
