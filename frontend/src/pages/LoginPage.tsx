import { LockOutlined } from "@mui/icons-material";
import { Alert, Avatar, Box, Button, Paper, TextField, Typography } from "@mui/material";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function LoginPage() {
  const navigate = useNavigate(); const [error, setError] = useState("");
  const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const form = new FormData(event.currentTarget); try { const { data } = await api.post("/auth/login", { username: form.get("username"), password: form.get("password") }); localStorage.setItem("crtnm-token", data.access_token); navigate("/"); } catch { setError("Sign-in failed. Check your username and password."); } };
  return <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2 }}><Paper elevation={8} sx={{ p: 4, width: "100%", maxWidth: 420 }}><Box sx={{ display: "grid", placeItems: "center", mb: 3 }}><Avatar sx={{ bgcolor: "primary.main", mb: 1 }}><LockOutlined /></Avatar><Typography variant="h5">CRTNM Secure Access</Typography></Box>{error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}<Box component="form" onSubmit={submit} sx={{ display: "grid", gap: 2 }}><TextField required name="username" label="Username" autoFocus /><TextField required name="password" label="Password" type="password" /><Button type="submit" variant="contained" size="large">Sign in</Button></Box></Paper></Box>;
}

