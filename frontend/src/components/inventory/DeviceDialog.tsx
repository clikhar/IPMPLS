import { FormEvent, useEffect, useState } from "react";

import {
    Box,
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    MenuItem,
    TextField
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

const defaultForm: CreateDeviceRequest = {
    station_id: 0,
    name: "",
    device_type: "ler",
    vendor: "neon",
    management_ip: "",
    protocol: "ssh",
    connection_username: "",
    password: ""
};

export default function DeviceDialog({
    open,
    loading,
    stations,
    onClose,
    onSubmit,
    mode,
    device
}: Props) {

    const [form, setForm] =
        useState<CreateDeviceRequest>(defaultForm);

    useEffect(() => {

        if (!open) return;

        if (mode === "edit" && device) {

            setForm({
                station_id: device.station_id,
                name: device.name,
                device_type: device.device_type,
                vendor: device.vendor,
                management_ip: device.management_ip,
                protocol: device.protocol,
                connection_username: device.connection_username,
                password: ""
            });

        } else {

            setForm(defaultForm);

        }

    }, [open, mode, device]);

    function submit(event: FormEvent<HTMLFormElement>) {

        event.preventDefault();

        onSubmit(form);

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

                    {mode === "create"
                        ? "Add Device"
                        : "Edit Device"}

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
                        label="Station"
                        value={form.station_id}
                        onChange={(e) =>
                            setForm({
                                ...form,
                                station_id: Number(e.target.value)
                            })
                        }
                    >

                        {stations.map((station) => (

                            <MenuItem
                                key={station.id}
                                value={station.id}
                            >
                                {station.name} - {station.division}
                            </MenuItem>

                        ))}

                    </TextField>

                    <TextField
                        required
                        label="Device Name"
                        value={form.name}
                        onChange={(e) =>
                            setForm({
                                ...form,
                                name: e.target.value
                            })
                        }
                    />

                    <TextField
                        select
                        required
                        label="Device Type"
                        value={form.device_type}
                        onChange={(e) =>
                            setForm({
                                ...form,
                                device_type: e.target.value
                            })
                        }
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
                        label="Vendor"
                        value={form.vendor}
                        onChange={(e) =>
                            setForm({
                                ...form,
                                vendor: e.target.value
                            })
                        }
                    />

                    <TextField
                        required
                        label="Management IP"
                        value={form.management_ip}
                        onChange={(e) =>
                            setForm({
                                ...form,
                                management_ip: e.target.value
                            })
                        }
                    />

                    <TextField
                        select
                        required
                        label="Protocol"
                        value={form.protocol}
                        onChange={(e) =>
                            setForm({
                                ...form,
                                protocol: e.target.value
                            })
                        }
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
                        label="Username"
                        value={form.connection_username}
                        onChange={(e) =>
                            setForm({
                                ...form,
                                connection_username: e.target.value
                            })
                        }
                    />

                    <TextField
                        type="password"
                        required={mode === "create"}
                        label={
                            mode === "create"
                                ? "Password"
                                : "New Password (leave blank to keep existing)"
                        }
                        value={form.password}
                        onChange={(e) =>
                            setForm({
                                ...form,
                                password: e.target.value
                            })
                        }
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

                        {mode === "create"
                            ? "Create"
                            : "Update"}

                    </Button>

                </DialogActions>

            </Box>

        </Dialog>

    );

}