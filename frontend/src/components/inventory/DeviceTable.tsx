import {
    Backup,
    Delete,
    Edit,
    NetworkCheck
} from "@mui/icons-material";

import {
    Button,
    Card,
    CardContent,
    Chip,
    Stack
} from "@mui/material";

import {
    DataGrid,
    GridColDef
} from "@mui/x-data-grid";

import { Device } from "../../types/inventory";

interface Props {

    devices: Device[];

    loading: boolean;

    onTest(id: number): void;

    onBackup(id: number): void;

    onEdit(device: Device): void;

    onDelete(device: Device): void;

}

export default function DeviceTable({

    devices,
    loading,
    onTest,
    onBackup,
    onEdit,
    onDelete

}: Props) {

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

            renderCell: ({ value }) => (

                <Chip
                    size="small"
                    label={value.toUpperCase()}
                />

            )

        },

        {
            field: "operations",

            headerName: "Operations",

            sortable: false,

            filterable: false,

            flex: 2,

            renderCell: ({ row }) => (

                <Stack
                    direction="row"
                    spacing={1}
                >

                    <Button
                        size="small"
                        startIcon={<NetworkCheck />}
                        onClick={() => onTest(row.id)}
                    >
                        Test
                    </Button>

                    <Button
                        size="small"
                        startIcon={<Backup />}
                        onClick={() => onBackup(row.id)}
                    >
                        Backup
                    </Button>

                    <Button
                        size="small"
                        startIcon={<Edit />}
                        onClick={() => onEdit(row)}
                    >
                        Edit
                    </Button>

                    <Button
                        size="small"
                        color="error"
                        startIcon={<Delete />}
                        onClick={() => onDelete(row)}
                    >
                        Delete
                    </Button>

                </Stack>

            )

        }

    ];

    return (

        <Card>

            <CardContent sx={{ height: 550 }}>

                <DataGrid
                    rows={devices}
                    columns={columns}
                    loading={loading}
                    disableRowSelectionOnClick
                />

            </CardContent>

        </Card>

    );

}