import {
    Router,
    Hub,
    Storage,
    Dns,
    Phone,
    Memory,
    Computer,
    Lan,
} from "@mui/icons-material";

import {
    Box,
    Chip,
    Paper,
    Stack,
    Typography,
} from "@mui/material";

interface RailwayNodeProps {
    name: string;
    vendor: string;
    ip: string;
    deviceType: string;
    status?: "online" | "offline" | "warning";
}

function getIcon(type: string) {

    switch (type.toLowerCase()) {

        case "ler":
            return <Router color="primary" />;

        case "l3_switch":
            return <Hub color="primary" />;

        case "l2_switch":
            return <Lan color="primary" />;

        case "server":
            return <Dns color="primary" />;

        case "gpon":
            return <Storage color="primary" />;

        case "fxs_gateway":
            return <Phone color="primary" />;

        case "voip_gateway":
            return <Phone color="primary" />;

        default:
            return <Computer color="primary" />;
    }
}

function chipColor(status: string) {

    switch (status) {

        case "online":
            return "success";

        case "warning":
            return "warning";

        case "offline":
            return "error";

        default:
            return "default";
    }
}

export default function RailwayNode({

    name,
    vendor,
    ip,
    deviceType,
    status = "online",

}: RailwayNodeProps) {

    return (

        <Paper
            elevation={5}
            sx={{
                width: 210,
                borderRadius: 2,
                p: 1.5,
                border: "1px solid #1976d2",
                backgroundColor: "#111c2e",
                cursor: "pointer",

                "&:hover": {
                    borderColor: "#00b8d4",
                    transform: "scale(1.02)",
                    transition: "0.15s",
                },
            }}
        >

            <Stack
                direction="row"
                spacing={1}
                alignItems="center"
            >

                {getIcon(deviceType)}

                <Typography
                    variant="subtitle2"
                    fontWeight={700}
                >
                    {name}
                </Typography>

            </Stack>

            <Typography
                variant="caption"
                color="text.secondary"
            >
                {vendor}
            </Typography>

            <Typography
                variant="body2"
                sx={{
                    mt: .5,
                    fontFamily: "monospace"
                }}
            >
                {ip}
            </Typography>

            <Box
                sx={{
                    mt: 1
                }}
            >

                <Chip
                    size="small"
                    label={status.toUpperCase()}
                    color={chipColor(status)}
                />

            </Box>

        </Paper>
    );
}