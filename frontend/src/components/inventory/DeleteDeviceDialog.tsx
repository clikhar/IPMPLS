import {
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Typography
} from "@mui/material";

import { Device } from "../../types/inventory";

interface Props {

    open: boolean;

    loading: boolean;

    device: Device | null;

    onClose(): void;

    onDelete(): void;

}

export default function DeleteDeviceDialog({

    open,
    loading,
    device,
    onClose,
    onDelete

}: Props) {

    return (

        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="xs"
            fullWidth
        >

            <DialogTitle>

                Delete Device

            </DialogTitle>

            <DialogContent>

                <Typography>

                    Are you sure you want to delete

                </Typography>

                <Typography
                    sx={{
                        mt: 2,
                        fontWeight: "bold"
                    }}
                >

                    {device?.name}

                </Typography>

                <Typography
                    variant="body2"
                    color="text.secondary"
                >

                    {device?.management_ip}

                </Typography>

                <Typography
                    sx={{ mt: 2 }}
                    color="error"
                >

                    This action cannot be undone.

                </Typography>

            </DialogContent>

            <DialogActions>

                <Button
                    onClick={onClose}
                >
                    Cancel
                </Button>

                <Button
                    color="error"
                    variant="contained"
                    onClick={onDelete}
                    disabled={loading}
                >
                    Delete
                </Button>

            </DialogActions>

        </Dialog>

    );

}