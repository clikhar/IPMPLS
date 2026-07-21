import {
    Alert,
    Box,
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Divider,
    Typography
} from "@mui/material";

import { ConnectionResult } from "../../types/inventory";

interface Props {

    open: boolean;

    result: ConnectionResult | null;

    error: string | null;

    onClose(): void;

}

export default function ConnectionDialog({

    open,
    result,
    error,
    onClose

}: Props) {

    return (

        <Dialog
            open={open}
            onClose={onClose}
            fullWidth
            maxWidth="sm"
        >

            <DialogTitle>
                Device Connection Test
            </DialogTitle>

            <DialogContent>

                {error && (

                    <Alert severity="error">
                        {error}
                    </Alert>

                )}

                {!error && result && (

                    <Box>

                        <Typography
                            variant="h6"
                            color="success.main"
                            gutterBottom
                        >
                            Connection Successful
                        </Typography>

                        <Divider sx={{ mb: 2 }} />

                        <Typography variant="subtitle2">
                            Hostname
                        </Typography>

                        <Typography sx={{ mb: 2 }}>
                            {result.hostname}
                        </Typography>

                        <Typography variant="subtitle2">
                            Prompt
                        </Typography>

                        <Typography sx={{ mb: 2 }}>
                            {result.prompt}
                        </Typography>

                        <Typography variant="subtitle2">
                            Version
                        </Typography>

                        <Typography>

                            {result.version ??
                                "Unknown"}

                        </Typography>

                    </Box>

                )}

            </DialogContent>

            <DialogActions>

                <Button
                    onClick={onClose}
                    variant="contained"
                >
                    Close
                </Button>

            </DialogActions>

        </Dialog>

    );

}