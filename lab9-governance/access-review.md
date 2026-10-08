# Lab 9 Step 2: access review of `Agentic Bootcamp/APAutomation_Sagar`

Read-only review, 2026-10-08, tenant Training. No assignment was added, changed or removed.
Colleagues are shown by role and count only; no emails or ids.

## Who can reach the folder

| Principal | Kind | Folder roles | Where it comes from |
|-----------|------|--------------|---------------------|
| Agentic Bootcamp Participants | Group | Automation Developer, Folder Administrator | Inherited from Agentic Bootcamp |
| Sagar Agrawal (me) | User | Automation Developer, Folder Administrator | Inherited from Agentic Bootcamp |
| 8 other participants | Users | Automation Developer, Folder Administrator | Inherited from Agentic Bootcamp (individual grants, same as the group) |
| 1 other user | User | Automation Developer, Automation Publisher, Folder Administrator | Inherited from Agentic Bootcamp |
| 1 other user | User | Folder Administrator | Inherited from Agentic Bootcamp |
| Agentic Labs Robot | Robot | Automation User | Assigned on this folder AND inherited from Agentic Bootcamp |

Total: 13 entries (1 group, 11 users, 1 robot). The only direct assignment on this folder is the robot.
Effective folder access for me (check-access, Folder scope): Automation Developer and Folder Administrator, on
both `APAutomation_Sagar` and `Agentic Bootcamp`, through my user grant and the participant group.

## My tenant groups

Administrators, Agentic Bootcamp Participants, Everyone, Action Center Commercial Sales, Command Center Admins,
TAMQBR.

## My tenant roles (check-access per service; 13 = unfiltered total)

| Service | Role | Source |
|---------|------|--------|
| Orchestrator | Orchestrator Administrator | via Administrators |
| Orchestrator | Solutions Administrator | via Administrators |
| Orchestrator | Allow to be Automation Developer | direct |
| Data Service | Data Service Administrator, Data Writer, Designer | via Administrators |
| Document Understanding | DU Administrator | via Administrators |
| IXP | IXP Service Admin | via Administrators |
| IXP | IXP Project Admin (one project) | direct and via Administrators |
| Process Mining | Administrator | via Administrators |
| Test Manager | Test Manager Administrator | via Administrators |
| Test Manager | Project Creator | via Administrators and Everyone |
| Organization | Licensing Administrator | via Administrators |

## Broader than this solution needs

1. **Participant group = Folder Administrator on Agentic Bootcamp (known, accepted).** Every participant can
   manage, change or delete anything in my folder, and I in theirs. Deliberate: Lab 2 creates the solution
   sub-folder. After the bootcamp, Automation Developer on the own folder only would be enough.
2. **Individual participant grants duplicate the group grant.** Same breadth, but they stay if someone leaves
   the group. Redundant.
3. **Two other users hold Folder Administrator (one also Automation Publisher)** on the parent, so on every
   participant folder. Likely facilitators; confirm with the facilitator.
4. **My membership in the tenant Administrators group.** It gives tenant-wide admin on Orchestrator, Data
   Service, Document Understanding, IXP, Process Mining, Test Manager and licensing. The solution only needs
   Automation Developer in my folder, Data Writer on my entity and access to my IXP project. Highest-impact
   finding: a mistake in any lab could reach other participants' data and tenant settings.
5. **Groups unrelated to the bootcamp** (Action Center Commercial Sales, Command Center Admins, TAMQBR) add
   access outside this solution's scope.
6. **Robot assigned twice** (direct + inherited Automation User). Harmless; Automation User is the right,
   minimal role for running the jobs.
