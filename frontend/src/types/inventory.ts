export interface Station {
    id: number;
    name: string;
    division: string;
}

export interface Device {
    id: number;
    station_id: number;
    name: string;
    device_type: string;
    vendor: string;
    model: string | null;
    management_ip: string;
    protocol: string;
}

export interface CreateDeviceRequest {
    station_id: number;
    name: string;
    device_type: string;
    vendor: string;
    management_ip: string;
    protocol: string;
    connection_username: string;
    password: string;
}

export interface ConnectionResult {
    device_id: number;
    hostname: string;
    prompt: string;
    version: string | null;
}