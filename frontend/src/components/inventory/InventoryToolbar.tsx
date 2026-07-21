import { Add } from "@mui/icons-material";
import {
    Box,
    Button,
    Stack,
    Typography
} from "@mui/material";

interface Props {
    onAdd(): void;
}

export default function InventoryToolbar({
    onAdd
}: Props) {

    return (
        <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
            sx={{ mb: 2 }}
        >
            <Box>

                <Typography variant="h4">
                    Device Inventory
                </Typography>

                <Typography color="text.secondary">
                    Managed Railway Network Equipment
                </Typography>

            </Box>

            <Button
                variant="contained"
                startIcon={<Add />}
                onClick={onAdd}
            >
                Add Device
            </Button>

        </Stack>
    );

}