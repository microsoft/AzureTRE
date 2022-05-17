import { User } from "./user";

export interface Operation {
    resourceId: string,
    resourcePath: string,
    resourceVersion: string,
    status: string,
    action: string,
    message: string
    createdWhen: number,
    updatedWhen: number,
    user: User
}

