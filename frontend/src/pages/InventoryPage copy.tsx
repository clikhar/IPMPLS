import { Alert, Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api } from "../api";
import DeviceTable from "../components/inventory/DeviceTable";  
import {
  Add,
  Router,
  NetworkCheck,
  Backup,
  Edit,
  Delete
} from "@mui/icons-material";

type Station = { id: number; name: string; division: string };
type Device = { id: number; station_id: number; name: string; device_type: string; vendor: string; model: string | null; management_ip: string; protocol: string };
type ConnectionResult = {
    device_id: number;
    hostname: string;
    prompt: string;
    version: string | null;
};
//const columns: GridColDef<Device>[] = [{ field: "name", headerName: "Device", flex: 1.1 }, { field: "vendor", headerName: "Vendor", flex: .8 }, { field: "device_type", headerName: "Type", flex: .9 }, { field: "management_ip", headerName: "Management IP", flex: 1 }, { field: "protocol", headerName: "Protocol", flex: .6, renderCell: ({ value }) => <Chip size="small" label={value.toUpperCase()} /> }];

export default function InventoryPage() 
                    {   const cache = useQueryClient();
                        const [open, setOpen] = useState(false); 
                        const devices = useQuery({ queryKey: ["devices"], queryFn: () => api.get<Device[]>("/devices").then((r) => r.data) });
                        const stations = useQuery({ queryKey: ["stations"], queryFn: () => api.get<Station[]>("/stations").then((r) => r.data) }); 
                        const create = useMutation({ mutationFn: (payload: object) => api.post("/devices", payload), onSuccess: () => { cache.invalidateQueries({ queryKey: ["devices"] }); setOpen(false); } }); 
                        const [connectionDialog, setConnectionDialog] = useState<ConnectionResult | null>(null);
                        const [connectionError, setConnectionError] = useState<string | null>(null);
                        const testConnection = useMutation({
                                mutationFn: (deviceId: number) =>
                                    api
                                        .post<ConnectionResult>(
                                            `/devices/${deviceId}/connection-test`
                                        )
                                        .then(r => r.data),

                                onSuccess: (data) => {
                                    setConnectionError(null);
                                    setConnectionDialog(data);
                                },

                                onError: (err: any) => {
                                    setConnectionDialog(null);
                                    setConnectionError(
                                        err?.response?.data?.detail ??
                                        "Connection failed."
                                    );
                                }
                            });

                        const backupDevice = useMutation({
                                    mutationFn: (deviceId: number) =>
                                        api.post(`/devices/${deviceId}/backups`),

                                    onSuccess: () => {
                                        alert("Backup completed.");
                                    },

                                    onError: () => {
                                        alert("Backup failed.");
                                    }
                                });
                        const columns: GridColDef<Device>[] = [
                                {
                                    field: "name",
                                    headerName: "Device",
                                    flex: 1.2
                                },
                                {
                                    field: "vendor",
                                    headerName: "Vendor",
                                    flex: .8
                                },
                                {
                                    field: "device_type",
                                    headerName: "Type",
                                    flex: .8
                                },
                                {
                                    field: "management_ip",
                                    headerName: "Management IP",
                                    flex: 1
                                },
                                {
                                    field: "protocol",
                                    headerName: "Protocol",
                                    flex: .6,
                                    renderCell: ({ value }) =>
                                        <Chip
                                            size="small"
                                            label={value.toUpperCase()}
                                        />
                                },
                                {
                                    field: "operations",
                                    headerName: "Operations",
                                    flex: 1.8,
                                    sortable: false,
                                    filterable: false,

                                    renderCell: ({ row }) => (
                                        <Stack
                                            direction="row"
                                            spacing={1}
                                        >
                                            <Button
                                                size="small"
                                                startIcon={<NetworkCheck />}
                                                onClick={() =>
                                                    testConnection.mutate(row.id)
                                                }
                                            >
                                                Test
                                            </Button>

                                            <Button
                                                size="small"
                                                startIcon={<Backup />}
                                                onClick={() =>
                                                    backupDevice.mutate(row.id)
                                                }
                                            >
                                                Backup
                                            </Button>

                                            <Button
                                                size="small"
                                                startIcon={<Edit />}
                                            >
                                                Edit
                                            </Button>

                                            <Button
                                                size="small"
                                                color="error"
                                                startIcon={<Delete />}
                                            >
                                                Delete
                                            </Button>
                                        </Stack>
                                    )
                                }
                            ];
                        const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); 
                        const data = new FormData(event.currentTarget); 
                        
                        
                        create.mutate({ station_id: Number(data.get("station_id")), 
                                         name: data.get("name"), 
                                         device_type: data.get("device_type"), 
                                         vendor: data.get("vendor"), 
                                         management_ip: data.get("management_ip"), 
                                         protocol: data.get("protocol"), 
                                         connection_username: data.get("connection_username"), 
                                         password: data.get("password") }); 
                        }; 
                         return <>
                         <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                            <Box>
                                <Typography variant="h4">Device Inventory</Typography>
                                <Typography color="text.secondary">Managed railway network equipment</Typography>
                            </Box>
                            <Button variant="contained" startIcon={<Add />} onClick={() => setOpen(true)}>Add device
                            </Button>
                        </Stack>{devices.isError && <Alert severity="error">Inventory could not be loaded.</Alert>}
                        <Card>
                            <CardContent sx={{ height: 520 }}>
                                <DataGrid rows={devices.data ?? []} columns={columns} loading={devices.isLoading} disableRowSelectionOnClick />
                                </CardContent>
                                </Card>
                                <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
                                    <Box component="form" onSubmit={submit}>
                                        <DialogTitle>Add managed device</DialogTitle>
                                        <DialogContent sx={{ display: "grid", gap: 2, pt: "16px !important" }}>
                                            <TextField required select name="station_id" label="Station">{stations.data?.map((station) => 
                                                <MenuItem key={station.id} value={station.id}>{station.name} - {station.division}
                                                </MenuItem>)}
                                            </TextField>
                                            <TextField required name="name" label="Device name" />
                                            <TextField required select name="device_type" label="Device type" defaultValue="ler">
                                                <MenuItem value="ler">NEON LER</MenuItem>
                                                <MenuItem value="l2_switch">L2 Switch</MenuItem>
                                                <MenuItem value="l3_switch">L3 Switch</MenuItem>
                                                <MenuItem value="gpon">GPON</MenuItem>
                                                <MenuItem value="fxs_gateway">FXS Gateway</MenuItem>
                                                <MenuItem value="voip_gateway">VOIP Gateway</MenuItem>
                                            </TextField>
                                            <TextField required name="vendor" label="Vendor" defaultValue="neon" />
                                            <TextField required name="management_ip" label="Management IP" />
                                            <TextField required select name="protocol" label="Protocol" defaultValue="ssh">
                                                <MenuItem value="ssh">SSH</MenuItem>
                                                <MenuItem value="telnet">Telnet</MenuItem>
                                            </TextField>
                                            <TextField required name="connection_username" label="Connection username" />
                                            <TextField required name="password" type="password" label="Connection password" />
                                        </DialogContent>
                                        <DialogActions>
                                            <Button onClick={() => setOpen(false)}>Cancel</Button>
                                            <Button type="submit" variant="contained" disabled={create.isPending}>
                                                Save device
                                            </Button>
                                        </DialogActions>
                                    </Box>
                                </Dialog>
                                <Dialog
    open={connectionDialog !== null || connectionError !== null}
    onClose={() => {
        setConnectionDialog(null);
        setConnectionError(null);
    }}
>
    <DialogTitle>
        Connection Test
    </DialogTitle>

    <DialogContent>

        {connectionError ? (

            <Alert severity="error">
                {connectionError}
            </Alert>

        ) : (

            <>
                <Typography>
                    Hostname:
                    {connectionDialog?.hostname}
                </Typography>

                <Typography>
                    Prompt:
                    {connectionDialog?.prompt}
                </Typography>

                <Typography>
                    Version:
                    {connectionDialog?.version}
                </Typography>
            </>
        )}

    </DialogContent>

    <DialogActions>

        <Button
            onClick={() => {
                setConnectionDialog(null);
                setConnectionError(null);
            }}
        >
            Close
        </Button>

    </DialogActions>
</Dialog>
                            </>; }
