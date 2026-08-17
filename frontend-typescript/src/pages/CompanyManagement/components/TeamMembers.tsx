import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SectionHead } from "@/components/ui/SectionHead";
import Button, { ConfirmDeleteButton } from "@/components/ui/Button";
import {
  listCompanyUsers,
  inviteUser,
  removeCompanyUser,
  updateUserRole,
  CompanyUser,
} from "@/api/adminManagementApi";

const USERS_QUERY_KEY = ["companyUsers"];

function roleBadgeClass(role: CompanyUser["role"]): string {
  if (role === "admin" || role === "superuser") return "bg-slate-700 text-white";
  return "bg-slate-100 text-slate-700";
}

function MemberCard({
  member,
  onPromote,
  onDemote,
  onRemove,
  isMutating,
}: {
  member: CompanyUser;
  onPromote: () => void;
  onDemote: () => void;
  onRemove: () => void;
  isMutating: boolean;
}) {
  const displayName =
    `${member.first_name ?? ""} ${member.last_name ?? ""}`.trim() || member.email;

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex items-center justify-between gap-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm text-slate-900 truncate">{displayName}</span>
          <span
            className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded ${roleBadgeClass(member.role)}`}
          >
            {member.role}
          </span>
          {member.status === "pending" && (
            <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">
              pending
            </span>
          )}
        </div>
        <div className="text-xs text-slate-500 truncate">{member.email}</div>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {member.role === "admin" ? (
          <Button variant="outline" onClick={onDemote} disabled={isMutating}>
            Demote
          </Button>
        ) : (
          <Button variant="outline" onClick={onPromote} disabled={isMutating}>
            Promote
          </Button>
        )}
        <ConfirmDeleteButton onConfirm={onRemove} disabled={isMutating}>
          Remove
        </ConfirmDeleteButton>
      </div>
    </div>
  );
}

export function TeamMembers() {
  const queryClient = useQueryClient();
  const [inviteEmail, setInviteEmail] = useState("");

  const usersQuery = useQuery({
    queryKey: USERS_QUERY_KEY,
    queryFn: listCompanyUsers,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });

  const inviteMutation = useMutation({
    mutationFn: () => inviteUser({ email: inviteEmail.trim() }),
    onSuccess: () => {
      setInviteEmail("");
      invalidate();
    },
  });

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: "admin" | "user" }) =>
      updateUserRole(userId, role),
    onSuccess: invalidate,
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) => removeCompanyUser(userId),
    onSuccess: invalidate,
  });

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    inviteMutation.mutate();
  };

  const members = usersQuery.data ?? [];

  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6">
      <SectionHead title="Team members" hint={`${members.length} member(s)`} />

      <form onSubmit={handleInvite} className="flex gap-2 mb-4">
        <input
          type="email"
          value={inviteEmail}
          onChange={(e) => setInviteEmail(e.target.value)}
          placeholder="teammate@example.org"
          className="border p-2 rounded w-full max-w-sm"
        />
        <Button type="submit" variant="secondary" disabled={inviteMutation.isPending}>
          Invite
        </Button>
      </form>
      {inviteMutation.isError && (
        <p className="text-xs text-red-500 mb-4">
          Couldn't send that invite — check the email and try again.
        </p>
      )}

      {usersQuery.isPending ? (
        <div className="text-sm text-slate-500">Loading team...</div>
      ) : usersQuery.isError ? (
        <div className="text-sm text-red-500">Failed to load team members.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {members.map((member) => (
            <MemberCard
              key={member.id}
              member={member}
              onPromote={() => roleMutation.mutate({ userId: member.id, role: "admin" })}
              onDemote={() => roleMutation.mutate({ userId: member.id, role: "user" })}
              onRemove={() => removeMutation.mutate(member.id)}
              isMutating={
                (roleMutation.isPending &&
                  roleMutation.variables?.userId === member.id) ||
                (removeMutation.isPending && removeMutation.variables === member.id)
              }
            />
          ))}
        </div>
      )}
      {(roleMutation.isError || removeMutation.isError) && (
        <p className="text-xs text-red-500 mt-3">
          That action wasn't allowed — you may be removing/demoting the last admin.
        </p>
      )}
    </section>
  );
}
