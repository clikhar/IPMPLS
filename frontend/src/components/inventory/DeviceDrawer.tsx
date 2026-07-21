import CloseIcon from "@mui/icons-material/Close";

import {
    Box,
    Drawer,
    IconButton,
    Tab,
    Tabs,
    Typography,
    Divider
} from "@mui/material";

import { useState } from "react";

import { Device } from "../../types/inventory";

interface Props {

    open: boolean;

    device: Device | null;

    onClose(): void;

}

export default function DeviceDrawer({

    open,
    device,
    onClose

}: Props) {

    const [tab, setTab] = useState(0);

    return (

        <Drawer
            anchor="right"
            open={open}
            onClose={onClose}
            PaperProps={{
                sx: {
                    width: 650
                }
            }}
        >

            <Box
                sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    p: 2
                }}
            >

                <Typography variant="h6">

                    {device?.name}

                </Typography>

                <IconButton onClick={onClose}>

                    <CloseIcon />

                </IconButton>

            </Box>

            <Divider />

            <Tabs
                value={tab}
                onChange={(_, value) => setTab(value)}
                variant="scrollable"
            >

                <Tab label="Overview" />

                <Tab label="Terminal" />

                <Tab label="Config" />

                <Tab label="Interfaces" />

                <Tab label="LLDP" />

                <Tab label="Logs" />

            </Tabs>

            <Divider />

            <Box sx={{ p: 3 }}>

                {tab === 0 && (

                    <Box
                        sx={{
                            display: "grid",
                            gridTemplateColumns: "180px 1fr",
                            rowGap: 2
                        }}
                    >

                        <Typography fontWeight="bold">
                            Device Name
                        </Typography>

                        <Typography>
                            {device?.name}
                        </Typography>

                        <Typography fontWeight="bold">
                            Vendor
                        </Typography>

                        <Typography>
                            {device?.vendor}
                        </Typography>

                        <Typography fontWeight="bold">
                            Device Type
                        </Typography>

                        <Typography>
                            {device?.device_type}
                        </Typography>

                        <Typography fontWeight="bold">
                            Management IP
                        </Typography>

                        <Typography>
                            {device?.management_ip}
                        </Typography>

                        <Typography fontWeight="bold">
                            Protocol
                        </Typography>

                        <Typography>
                            {device?.protocol}
                        </Typography>

                        <Typography fontWeight="bold">
                            Username
                        </Typography>

                        <Typography>
                            {device?.connection_username}
                        </Typography>

                        <Typography fontWeight="bold">
                            Station ID
                        </Typography>

                        <Typography>
                            {device?.station_id}
                        </Typography>

                    </Box>

                )}

                {tab === 1 && (

                    <Typography>

                        Browser Terminal will be implemented in the next milestone.

                    </Typography>

                )}

                {tab === 2 && (

                    <Typography>

                        Configuration Backup Manager coming next.

                    </Typography>

                )}

                {tab === 3 && (

                    <Typography>

                        Interface statistics coming next.

                    </Typography>

                )}

                {tab === 4 && (

                    <Typography>

                        LLDP topology coming next.

                    </Typography>

                )}

                {tab === 5 && (

                    <Typography>

                        Audit logs coming next.

                    </Typography>

                )}

            </Box>

        </Drawer>

    );

}