import { FormEvent, useEffect, useState } from "react";

import {
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    MenuItem,
    TextField,
    Box
} from "@mui/material";

import {
    CreateDeviceRequest,
    Device,
    Station
} from "../../types/inventory";

interface Props {
    open: boolean;

    loading: boolean;

    stations: Station[];

    onClose(): void;

    onSubmit(payload: CreateDeviceRequest): void;

    mode: "create" | "edit";

    device?: Device | null;
}

export default function DeviceDialog({
    open,
    loading,
    stations,
    onClose,
    onSubmit,
    mode,
    device
}: Props) {

    function submit(event: FormEvent<HTMLFormElement>) {

        event.preventDefault();

        const data = new FormData(event.currentTarget);

        onSubmit({

            station_id: Number(data.get("station_id")),

            name: String(data.get("name")),

            device_type: String(data.get("device_type")),

            vendor: String(data.get("vendor")),

            management_ip: String(data.get("management_ip")),

            protocol: String(data.get("protocol")),

            connection_username: String(
                data.get("connection_username")
            ),

            password: String(
                data.get("password")
            )

        });

    }

    return (

        <Dialog
            open={open}
            onClose={onClose}
            fullWidth
            maxWidth="sm"
        >

            <Box
                component="form"
                onSubmit={submit}
            >

                <DialogTitle>
                    Add Device
                </DialogTitle>

                <DialogContent
                    sx={{
                        display: "grid",
                        gap: 2,
                        pt: "16px !important"
                    }}
                >

                    <TextField
                        select
                        required
                        name="station_id"
                        label="Station"
                    >
                        {stations.map(station => (

                            <MenuItem
                                key={station.id}
                                value={station.id}
                            >
                                {station.name}
                                {" - "}
                                {station.division}
                            </MenuItem>

                        ))}
                    </TextField>

                    <TextField
                        required
                        name="name"
                        label="Device Name"
                    />

                    <TextField
                        select
                        required
                        name="device_type"
                        label="Device Type"
                        defaultValue="ler"
                    >
                        <MenuItem value="ler">
                            NEON LER
                        </MenuItem>

                        <MenuItem value="l3_switch">
                            L3 Switch
                        </MenuItem>

                        <MenuItem value="l2_switch">
                            L2 Switch
                        </MenuItem>

                        <MenuItem value="gpon">
                            GPON
                        </MenuItem>

                        <MenuItem value="fxs_gateway">
                            FXS Gateway
                        </MenuItem>

                        <MenuItem value="voip_gateway">
                            VoIP Gateway
                        </MenuItem>

                    </TextField>

                    <TextField
                        required
                        name="vendor"
                        label="Vendor"
                        defaultValue="neon"
                    />

                    <TextField
                        required
                        name="management_ip"
                        label="Management IP"
                    />

                    <TextField
                        required
                        select
                        name="protocol"
                        label="Protocol"
                        defaultValue="ssh"
                    >
                        <MenuItem value="ssh">
                            SSH
                        </MenuItem>

                        <MenuItem value="telnet">
                            Telnet
                        </MenuItem>
                    </TextField>

                    <TextField
                        required
                        name="connection_username"
                        label="Username"
                    />

                    <TextField
                        required
                        type="password"
                        name="password"
                        label="Password"
                    />

                </DialogContent>

                <DialogActions>

                    <Button
                        onClick={onClose}
                    >
                        Cancel
                    </Button>

                    <Button
                        type="submit"
                        variant="contained"
                        disabled={loading}
                    >
                        Save
                    </Button>

                </DialogActions>

            </Box>

        </Dialog>

    );

}