# Conditional Access Policies and MFA

Conditional Access is a critical security feature in Microsoft Entra ID (formerly Azure Active Directory) that allows you to enforce access controls on the Azure TRE based on specific conditions. This includes requiring multi-factor authentication (MFA), restricting access by location, and more.

This guide covers how to configure Conditional Access Policies for the Azure TRE at both the TRE-wide level and per-workspace level.

## Overview

Conditional Access policies work by evaluating signals such as user identity, location, device state, and risk level to make access decisions. For a Trusted Research Environment, these policies help ensure that:

- Only authorized users can access the TRE
- Access is restricted based on location or network (e.g., specific regions or IP ranges)
- Multi-factor authentication is enforced for sensitive operations
- Devices meet security requirements before accessing research data

!!! info
    For detailed information about Conditional Access, refer to the [Microsoft Entra Conditional Access documentation](https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview).

## Prerequisites

Before configuring Conditional Access Policies:

1. You must have an [Microsoft Entra ID P1 or P2 license](https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview#license-requirements) to use Conditional Access features
2. You must have the appropriate permissions in Microsoft Entra ID (typically Global Administrator or Conditional Access Administrator role)
3. The Azure TRE must be deployed with the proper [Microsoft Entra ID integration](./auth.md)

## TRE-Wide Conditional Access Policies

TRE-wide policies apply to all users accessing the Azure TRE, regardless of workspace. These policies should be configured at the Microsoft Entra ID level and target the TRE applications.

### Identifying TRE Applications

The Azure TRE uses several Microsoft Entra ID applications as described in the [Authentication and Authorization documentation](./auth.md). The main applications to target in Conditional Access Policies are:

- **TRE API application**: Controls access to the TRE API
- **TRE UX**: The client application for the TRE portal
- **Workspace API applications**: Individual applications for each workspace (see [Workspace Applications](./identities/workspace.md))

!!! important "Covering New Workspaces"
    Since each workspace has its own Microsoft Entra ID application that is created on-demand, you must ensure your TRE-wide Conditional Access Policies automatically cover new workspaces. There are several strategies:

    1. **Use "All cloud apps" with exclusions** (Recommended for TRE-wide policies):
       - Select **All cloud apps** under **Cloud apps or actions**
       - Add specific exclusions if needed (e.g., exclude certain administrative apps)
       - This ensures all workspace applications are automatically covered, including future ones
       - Use this approach for critical policies like MFA requirements

    2. **Regularly update policies** (When using specific app selection):
       - When a new workspace is created, manually add its application to existing TRE-wide Conditional Access Policies
       - Set up a process to review and update policies when new workspaces are provisioned
       - This approach provides more granular control but requires ongoing maintenance

    3. **Use Azure AD Security Groups** (If AUTO_WORKSPACE_APP_REGISTRATION is enabled):
       - If using automated workspace app registration with group assignment, you can target the security groups in your Conditional Access Policies
       - See [Application Admin](./identities/application_admin.md) for more details on AUTO_WORKSPACE_GROUP_CREATION

### Recommended TRE-Wide Policies

#### 1. Require Multi-Factor Authentication (MFA)

Multi-factor authentication adds an essential layer of security by requiring users to verify their identity using multiple methods.

**To configure MFA for TRE:**

1. Navigate to **Microsoft Entra ID** > **Security** > **Conditional Access**
2. Select **+ New policy**
3. Give your policy a name (e.g., "TRE - Require MFA")
4. Under **Assignments**:
   - **Users**: Select the users or groups that will access the TRE
   - **Cloud apps or actions**: 
     - **Recommended**: Select **All cloud apps** to automatically cover all TRE applications including future workspace applications
     - **Alternative**: Select specific applications (TRE API, TRE UX, and all workspace applications), but remember to update this list when new workspaces are created
5. Under **Access controls** > **Grant**:
   - Select **Grant access**
   - Check **Require multi-factor authentication**
6. Set **Enable policy** to **On**
7. Select **Create**

!!! tip
    Consider using [Microsoft Entra ID Conditional Access template policies](https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-conditional-access-policy-common) as a starting point.

!!! warning "Using specific app selection"
    If you choose to select specific applications instead of "All cloud apps", you must update the policy each time a new workspace is created to ensure the workspace application is covered. This can lead to security gaps if forgotten. For critical policies like MFA, use "All cloud apps" to ensure comprehensive coverage.

#### 2. Require Compliant or Hybrid Joined Devices

For additional security, you can require that devices accessing the TRE are managed and meet your organization's compliance policies.

**To configure device compliance:**

1. Create a new Conditional Access Policy
2. Name the policy (e.g., "TRE - Require Compliant Device")
3. Under **Assignments**:
   - **Users**: Select TRE users or groups
   - **Cloud apps**: Select **All cloud apps** (recommended) or select specific TRE applications
4. Under **Access controls** > **Grant**:
   - Select **Grant access**
   - Check **Require device to be marked as compliant** or **Require Hybrid Azure AD joined device**
5. Enable and create the policy

For more information, see [Require device to be marked as compliant](https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-conditional-access-grant#require-device-to-be-marked-as-compliant).

#### 3. Block Access from Untrusted Locations

You may want to block access to the TRE from certain countries or regions for compliance or security reasons.

**To configure location-based restrictions:**

1. First, define [Named locations](https://learn.microsoft.com/en-us/entra/identity/conditional-access/location-condition) in Microsoft Entra ID
2. Create a new Conditional Access Policy
3. Name the policy (e.g., "TRE - Block Untrusted Locations")
4. Under **Assignments**:
   - **Users**: Select TRE users or groups
   - **Cloud apps**: Select **All cloud apps** (recommended) or select specific TRE applications
   - **Conditions** > **Locations**:
     - Configure **Yes**
     - Under **Exclude**, select the trusted named locations
5. Under **Access controls** > **Grant**:
   - Select **Block access**
6. Enable and create the policy

#### 4. Session Controls

Session controls allow you to enable limited experiences within cloud apps. For example, you can use session controls to enforce app-enforced restrictions or require the use of Conditional Access App Control.

For more information, see [Conditional Access: Session](https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-conditional-access-session).

## Per-Workspace Conditional Access Policies

Each workspace in the Azure TRE has its own Microsoft Entra ID application, which allows you to apply different Conditional Access Policies to different workspaces. This is particularly useful when different research projects have different security or compliance requirements.

### Workspace-Specific Location Restrictions

You can restrict access to specific workspaces based on geographic location or IP address ranges. This is useful for:

- Ensuring researchers only access data from approved locations
- Complying with data residency requirements
- Limiting access to on-premises networks via VPN

**To configure location-based access for a specific workspace:**

1. Identify the Workspace API application in Microsoft Entra ID
   - Navigate to **Microsoft Entra ID** > **App registrations**
   - Find the workspace application (typically named `<TRE_ID>-ws-<workspace_id>`)
2. Create or update Named locations in Microsoft Entra ID:
   - Navigate to **Microsoft Entra ID** > **Security** > **Conditional Access** > **Named locations**
   - Select **+ New location**
   - Choose between **Countries location** or **IP ranges location**
   - For IP ranges, enter the specific IP addresses or CIDR ranges (e.g., `203.0.113.0/24`)
   - Mark as **Trusted location** if appropriate
3. Create a new Conditional Access Policy:
   - Name it descriptively (e.g., "Workspace [workspace_id] - Restrict to Approved Locations")
   - Under **Assignments**:
     - **Users**: Select users who should access this workspace
     - **Cloud apps**: Select the specific workspace application
     - **Conditions** > **Locations**:
       - Configure **Yes**
       - Under **Include**, select **Any location**
       - Under **Exclude**, select the named locations you created
4. Under **Access controls** > **Grant**:
   - Select **Block access**
5. Enable and create the policy

!!! note
    When using IP-based Named locations, ensure you include all IP ranges from which legitimate access should occur, including VPN endpoints, office networks, and approved remote locations.

### Workspace-Specific MFA Requirements

Different workspaces may have different MFA requirements based on data sensitivity:

**To configure workspace-specific MFA:**

1. Create a Conditional Access Policy targeting the specific workspace application
2. Configure stricter MFA requirements (e.g., requiring MFA every time, not just once per session)
3. Consider using [Authentication strengths](https://learn.microsoft.com/en-us/entra/identity/authentication/concept-authentication-strengths) to require specific authentication methods for highly sensitive workspaces

## Testing Conditional Access Policies

Before enabling Conditional Access Policies in production:

1. Use **Report-only mode** to test policies without impacting users:
   - Set **Enable policy** to **Report-only**
   - Monitor [sign-in logs](https://learn.microsoft.com/en-us/entra/identity/monitoring-health/concept-sign-ins) to see how the policy would affect users
2. Test with a pilot group of users before rolling out to all TRE users
3. Use the [What If tool](https://learn.microsoft.com/en-us/entra/identity/conditional-access/what-if-tool) to simulate policy impacts

!!! warning
    Be careful not to lock yourself out! Always ensure there's a [break-glass account](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/security-emergency-access) excluded from Conditional Access Policies.

## Monitoring and Troubleshooting

### Sign-in Logs

Monitor Conditional Access Policy effectiveness using Microsoft Entra ID sign-in logs:

1. Navigate to **Microsoft Entra ID** > **Monitoring** > **Sign-in logs**
2. Filter by **Application** to see TRE-specific access attempts
3. Review the **Conditional Access** column to see which policies were applied
4. Check **Status** to identify blocked or failed sign-in attempts

For more information, see [Sign-in logs in Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/identity/monitoring-health/concept-sign-ins).

### Common Issues

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Users blocked unexpectedly | Policy scope too broad | Review user and location exclusions |
| MFA not prompted | Policy not targeting the right app | Verify the TRE applications are included in the policy |
| Location detection incorrect | IP address not in Named location | Update Named locations with correct IP ranges |
| Workspace access denied | Multiple conflicting policies | Review all policies targeting the workspace app |

### Audit Logs

Track changes to Conditional Access Policies:

1. Navigate to **Microsoft Entra ID** > **Monitoring** > **Audit logs**
2. Filter by **Service** = **Conditional Access**
3. Review policy creation, modification, and deletion events

## Best Practices

1. **Use Report-only mode first**: Always test new policies in report-only mode before enforcement
2. **Exclude break-glass accounts**: Ensure emergency access accounts are excluded from all Conditional Access Policies
3. **Document policies**: Maintain clear documentation of what each policy does and why it exists
4. **Regular reviews**: Periodically review and update policies as requirements change
5. **Principle of least privilege**: Apply the most restrictive policies appropriate for each workspace's data sensitivity
6. **Combine conditions carefully**: Multiple conditions create an AND relationship - ensure the combination makes sense
7. **Monitor regularly**: Review sign-in logs regularly to ensure policies are working as expected
8. **User communication**: Inform users about Conditional Access requirements before enforcement to reduce support requests

## Additional Resources

- [Microsoft Entra Conditional Access documentation](https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview)
- [Common Conditional Access policies](https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-conditional-access-policy-common)
- [Conditional Access: Conditions](https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-conditional-access-conditions)
- [Plan a Conditional Access deployment](https://learn.microsoft.com/en-us/entra/identity/conditional-access/plan-conditional-access)
- [Troubleshooting Conditional Access](https://learn.microsoft.com/en-us/entra/identity/conditional-access/troubleshoot-conditional-access)
- [Authentication and Authorization in Azure TRE](./auth.md)

## Related Documentation

- [Authentication and Authorization](./auth.md)
- [User Roles](../azure-tre-overview/user-roles.md)
- [Network Architecture](../azure-tre-overview/networking.md)
