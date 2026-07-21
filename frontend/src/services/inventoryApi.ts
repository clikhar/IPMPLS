import { api } from "../api";
import {
    Device,
    Station,
    CreateDeviceRequest,
    ConnectionResult
} from "../types/inventory";

export const inventoryApi = {

    getDevices() {
        return api.get<Device[]>("/devices");
    },

    getStations() {
        return api.get<Station[]>("/stations");
    },

    createDevice(payload: CreateDeviceRequest) {
        return api.post("/devices", payload);
    },

    testConnection(id: number) {
        return api.post<ConnectionResult>(
            `/devices/${id}/connection-test`
        );
    },

    backupDevice(id: number) {
        return api.post(
            `/devices/${id}/backups`
        );
    },
    
    updateDevice(id: number, payload: CreateDeviceRequest) {
        return api.put(
            `/devices/${id}`,
            payload
        );
    },

    deleteDevice(id: number) {
        return api.delete(
            `/devices/${id}`
        );
    },

};