export interface User {
    email: string,
    id: string,
    name: string,
    roleAssignments: Array<any>,
    roles: Array<string>
}