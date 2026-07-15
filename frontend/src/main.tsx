import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { createRoot } from "react-dom/client";
import App from "./App";
const theme = createTheme({ palette: { mode: "dark", primary: { main: "#00b8d4" }, background: { default: "#0b1220", paper: "#111c2e" } }, shape: { borderRadius: 10 } });
createRoot(document.getElementById("root")!).render(<QueryClientProvider client={new QueryClient()}><ThemeProvider theme={theme}><CssBaseline /><BrowserRouter><App /></BrowserRouter></ThemeProvider></QueryClientProvider>);

