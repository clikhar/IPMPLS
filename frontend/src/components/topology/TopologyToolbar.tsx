import {
    Search,
    Refresh,
    FitScreen,
    AccountTree,
    ViewTimeline,
} from "@mui/icons-material";

import {
    Box,
    IconButton,
    Paper,
    TextField,
    Tooltip,
    ToggleButton,
    ToggleButtonGroup,
} from "@mui/material";

interface Props {
    search: string;
    onSearch: (value: string) => void;

    direction: "TB" | "LR";
    onDirectionChange: (value: "TB" | "LR") => void;

    onRefresh: () => void;

    onFitView: () => void;
}

export default function TopologyToolbar({
    search,
    onSearch,
    direction,
    onDirectionChange,
    onRefresh,
    onFitView,
}: Props) {

    return (

        <Paper
            sx={{
                mb: 2,
                p: 1,
                display: "flex",
                alignItems: "center",
                gap: 2,
            }}
        >

            <TextField
                size="small"
                placeholder="Search device..."
                value={search}
                onChange={(e) => onSearch(e.target.value)}
                InputProps={{
                    startAdornment: <Search fontSize="small" />,
                }}
            />

            <Tooltip title="Refresh">

                <IconButton onClick={onRefresh}>

                    <Refresh />

                </IconButton>

            </Tooltip>

            <Tooltip title="Fit View">

                <IconButton onClick={onFitView}>

                    <FitScreen />

                </IconButton>

            </Tooltip>

            <ToggleButtonGroup
                value={direction}
                exclusive
                onChange={(_, value) => {

                    if (value)
                        onDirectionChange(value);

                }}
            >

                <ToggleButton value="TB">

                    <AccountTree />

                </ToggleButton>

                <ToggleButton value="LR">

                    <ViewTimeline />

                </ToggleButton>

            </ToggleButtonGroup>

        </Paper>

    );

}