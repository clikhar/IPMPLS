import { Alert, Snackbar } from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import InventoryToolbar from "../components/inventory/InventoryToolbar";
import DeviceTable from "../components/inventory/DeviceTable";
import DeviceDialog from "../components/inventory/DeviceDialog";

import { inventoryApi } from "../services/inventoryApi";
import { useDevices, useStations } from "../hooks/useInventory";
import DeleteDeviceDialog from "../components/inventory/DeleteDeviceDialog";
import {ConnectionResult,CreateDeviceRequest,Device} from "../types/inventory";
import DeviceDrawer from "../components/inventory/DeviceDrawer";
import ConnectionDialog from "../components/inventory/ConnectionDialog";

export default function InventoryPage() {
    const queryClient = useQueryClient();

    const devices = useDevices();
    const stations = useStations();

    const [openDialog, setOpenDialog] = useState(false);

    const [dialogMode, setDialogMode] =
        useState<"create" | "edit">("create");

    const [selectedDevice, setSelectedDevice] =
        useState<Device | null>(null);

    const [connectionResult, setConnectionResult] =
        useState<ConnectionResult | null>(null);
    
    const [deleteDialogOpen, setDeleteDialogOpen] =
        useState(false);

    const [deleteDeviceTarget, setDeleteDeviceTarget] =
        useState<Device | null>(null);
    const [drawerOpen, setDrawerOpen] =
        useState(false);

    const [drawerDevice, setDrawerDevice] =
        useState<Device | null>(null);

    const [snackbar, setSnackbar] = useState({
        open: false,
        message: "",
        severity: "success" as "success" | "error"
    });

    /*
     * Create Device
     */

    const createDevice = useMutation({
        mutationFn: (payload: CreateDeviceRequest) =>
            inventoryApi.createDevice(payload),

        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["devices"]
            });

            setOpenDialog(false);

            setSnackbar({
                open: true,
                severity: "success",
                message: "Device created successfully."
            });
        },

        onError: () => {
            setSnackbar({
                open: true,
                severity: "error",
                message: "Unable to create device."
            });
        }
    });

    /*
        * Edit Device
        */

    const updateDevice = useMutation({

        mutationFn: ({
            id,
            payload
        }: {
            id: number;
            payload: CreateDeviceRequest;
        }) =>
            inventoryApi.updateDevice(
                id,
                payload
            ),

        onSuccess: () => {

            queryClient.invalidateQueries({
                queryKey: ["devices"]
            });

            setOpenDialog(false);

            setSelectedDevice(null);

            setSnackbar({
                open: true,
                severity: "success",
                message: "Device updated."
            });

        },

        onError: () => {

            setSnackbar({
                open: true,
                severity: "error",
                message: "Unable to update device."
            });

        }

    });

    /*
     * Test Connection
     */

   /* const testConnection = useMutation({
        mutationFn: (id: number) =>
            inventoryApi
                .testConnection(id)
                .then(r => r.data),

        onSuccess: (data) => {
            setConnectionResult(data);

            setSnackbar({
                open: true,
                severity: "success",
                message: "Connection successful."
            });
        },

        onError: () => {
            setSnackbar({
                open: true,
                severity: "error",
                message: "Connection failed."
            });
        }
    });
*/
    const testConnection = useMutation({

            mutationFn: (id: number) =>
                inventoryApi
                    .testConnection(id)
                    .then(r => r.data),

            onSuccess: (data) => {

                setConnectionError(null);

                setConnectionResult(data);

            },

            onError: (error: any) => {

                setConnectionResult(null);

                /*setConnectionError(

                    error?.response?.data?.detail ??

                    "Connection failed."

                );*/
                let message = "Connection failed.";

                const detail = error?.response?.data?.detail;

                if (typeof detail === "string") {

                    message = detail;

                }
                else if (Array.isArray(detail)) {

                    message = detail
                        .map((d: any) => d.msg)
                        .join(", ");

                }

                setConnectionError(message);

            }

        });

    const deleteDevice = useMutation({

            mutationFn: (id: number) =>
                inventoryApi.deleteDevice(id),

            onSuccess: () => {

                queryClient.invalidateQueries({
                    queryKey: ["devices"]
                });

                setDeleteDialogOpen(false);

                setDeleteDeviceTarget(null);

                setSnackbar({

                    open: true,

                    severity: "success",

                    message: "Device deleted."

                });

            },

            onError: () => {

                setSnackbar({

                    open: true,

                    severity: "error",

                    message: "Unable to delete device."

                });

            }

        });
    /*
     * Backup
     */

    const backupDevice = useMutation({
        mutationFn: (id: number) =>
            inventoryApi.backupDevice(id),

        onSuccess: () => {
            setSnackbar({
                open: true,
                severity: "success",
                message: "Backup completed."
            });
        },

        onError: () => {
            setSnackbar({
                open: true,
                severity: "error",
                message: "Backup failed."
            });
        }
    });

    const [connectionError, setConnectionError] =
    useState<string | null>(null);

    return (
        <>

            <InventoryToolbar
                onAdd={() => {
                    setDialogMode("create");
                    setSelectedDevice(null);
                    setOpenDialog(true);
                }}
            />

            <DeviceTable
                devices={devices.data ?? []}
                loading={devices.isLoading}
                onTest={(id) => testConnection.mutate(id)}
                onBackup={(id) => backupDevice.mutate(id)}
                onEdit={(device) => {
                     setDrawerDevice(device);
                     setDrawerOpen(true);
                }}
                onDelete={(device: Device) => {
                    setDeleteDeviceTarget(device);
                    setDeleteDialogOpen(true);
                }}
            />

            <DeviceDialog
                open={openDialog}
                mode={dialogMode}
                device={selectedDevice}
                stations={stations.data ?? []}
                loading={
                    dialogMode === "create"
                        ? createDevice.isPending
                        : updateDevice.isPending
                }
                onClose={() => {

                    setOpenDialog(false);

                    setSelectedDevice(null);

                }}
                onSubmit={(payload) => {

                    if (dialogMode === "create") {

                        createDevice.mutate(payload);

                    } else {

                        updateDevice.mutate({

                            id: selectedDevice!.id,

                            payload

                        });

                    }

                }}
            />
            <DeleteDeviceDialog

                open={deleteDialogOpen}
                loading={deleteDevice.isPending}
                device={deleteDeviceTarget}
                onClose={() => {
                    setDeleteDialogOpen(false);
                    setDeleteDeviceTarget(null);
                }}
                onDelete={() => {
                    if (!deleteDeviceTarget) return;
                    deleteDevice.mutate(deleteDeviceTarget.id);
                }}

            />
            <ConnectionDialog

                open={
                    connectionResult !== null ||
                    connectionError !== null
                }

                result={connectionResult}

                error={connectionError}

                onClose={() => {

                    setConnectionResult(null);

                    setConnectionError(null);

                }}

            />
            <DeviceDrawer

                open={drawerOpen}

                device={drawerDevice}

                onClose={() => {

                    setDrawerOpen(false);

                    setDrawerDevice(null);

                }}

            />
            <Snackbar
                open={snackbar.open}
                autoHideDuration={3000}
                onClose={() =>
                    setSnackbar({
                        ...snackbar,
                        open: false
                    })
                }
            >
                <Alert
                    severity={snackbar.severity}
                    variant="filled"
                >
                    {snackbar.message}
                </Alert>
            </Snackbar>

        </>
    );
}