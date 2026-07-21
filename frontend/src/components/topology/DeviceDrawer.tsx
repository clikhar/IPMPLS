import {
    Close,
    Lan,
    Router,
    Hub,
    SettingsEthernet,
    MonitorHeart,
    Terminal,
    History,
    Backup,
} from "@mui/icons-material";

import {
    Box,
    Divider,
    Drawer,
    IconButton,
    List,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    Stack,
    Typography,
    Chip,
} from "@mui/material";

interface DeviceDrawerProps {
    open: boolean;
    onClose: () => void;
    device?: {
        id: string;
        name: string;
        vendor: string;
        ip: string;
        type: string;
    };
}

export default function DeviceDrawer({
    open,
    onClose,
    device,
}: DeviceDrawerProps) {

    return (
        <Drawer
            anchor="right"
            open={open}
            onClose={onClose}
        >
            <Box sx={{ width: 360 }}>

                <Stack
                    direction="row"
                    justifyContent="space-between"
                    alignItems="center"
                    p={2}
                >

                    <Typography variant="h6">
                        {device?.name ?? "Device"}
                    </Typography>

                    <IconButton onClick={onClose}>
                        <Close />
                    </IconButton>

                </Stack>

                <Divider />

                <Box p={2}>

                    <Chip
                        label={device?.type}
                        color="primary"
                        sx={{ mb: 2 }}
                    />

                    <Typography variant="body2">
                        Vendor
                    </Typography>

                    <Typography fontWeight={700}>
                        {device?.vendor}
                    </Typography>

                    <Typography
                        sx={{ mt: 2 }}
                        variant="body2"
                    >
                        Management IP
                    </Typography>

                    <Typography fontFamily="monospace">
                        {device?.ip}
                    </Typography>

                </Box>

                <Divider />

                <List>

                    <ListItemButton>
                        <ListItemIcon>
                            <Lan />
                        </ListItemIcon>
                        <ListItemText primary="Interfaces" />
                    </ListItemButton>

                    <ListItemButton>
                        <ListItemIcon>
                            <Router />
                        </ListItemIcon>
                        <ListItemText primary="Routing / MPLS" />
                    </ListItemButton>

                    <ListItemButton>
                        <ListItemIcon>
                            <Hub />
                        </ListItemIcon>
                        <ListItemText primary="LLDP Neighbors" />
                    </ListItemButton>

                    <ListItemButton>
                        <ListItemIcon>
                            <MonitorHeart />
                        </ListItemIcon>
                        <ListItemText primary="Monitoring" />
                    </ListItemButton>

                    <ListItemButton>
                        <ListItemIcon>
                            <SettingsEthernet />
                        </ListItemIcon>
                        <ListItemText primary="Configuration" />
                    </ListItemButton>

                    <ListItemButton>
                        <ListItemIcon>
                            <Terminal />
                        </ListItemIcon>
                        <ListItemText primary="Live Terminal" />
                    </ListItemButton>

                    <ListItemButton>
                        <ListItemIcon>
                            <Backup />
                        </ListItemIcon>
                        <ListItemText primary="Backup / Restore" />
                    </ListItemButton>

                    <ListItemButton>
                        <ListItemIcon>
                            <History />
                        </ListItemIcon>
                        <ListItemText primary="Audit History" />
                    </ListItemButton>

                </List>

            </Box>

        </Drawer>
    );
}