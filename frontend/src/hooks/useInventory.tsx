import { useQuery } from "@tanstack/react-query";
import { inventoryApi } from "../services/inventoryApi";

export function useDevices() {
    return useQuery({
        queryKey: ["devices"],
        queryFn: () =>
            inventoryApi
                .getDevices()
                .then(r => r.data)
    });
}

export function useStations() {
    return useQuery({
        queryKey: ["stations"],
        queryFn: () =>
            inventoryApi
                .getStations()
                .then(r => r.data)
    });
}