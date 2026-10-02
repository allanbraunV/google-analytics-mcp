"""Grants a service account Viewer on every GA account the caller can manage.

Uses Application Default Credentials, which must belong to a GA admin user and
include the https://www.googleapis.com/auth/analytics.manage.users scope.

Dry run by default; pass --apply to create the access bindings.

  python scripts/grant_sa_access.py ga4-mcp@PROJECT.iam.gserviceaccount.com [--apply]
"""

import argparse

import google.auth
from google.analytics import admin_v1alpha

SCOPES = [
    "https://www.googleapis.com/auth/analytics.manage.users",
    "https://www.googleapis.com/auth/analytics.readonly",
]
VIEWER_ROLE = "predefinedRoles/viewer"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("service_account")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    credentials, _ = google.auth.default(scopes=SCOPES)
    client = admin_v1alpha.AnalyticsAdminServiceClient(credentials=credentials)

    granted, already, failed = [], [], []
    for summary in client.list_account_summaries():
        account, name = summary.account, summary.display_name
        try:
            bindings = client.list_access_bindings(parent=account)
            if any(b.user == args.service_account for b in bindings):
                already.append(name)
                continue
            if args.apply:
                client.batch_create_access_bindings(
                    request=admin_v1alpha.BatchCreateAccessBindingsRequest(
                        parent=account,
                        requests=[
                            admin_v1alpha.CreateAccessBindingRequest(
                                parent=account,
                                access_binding=admin_v1alpha.AccessBinding(
                                    user=args.service_account,
                                    roles=[VIEWER_ROLE],
                                ),
                            )
                        ],
                    )
                )
            granted.append(name)
        except Exception as e:  # Usually: caller isn't an admin of this account.
            failed.append((name, str(e).splitlines()[0]))

    verb = "Granted" if args.apply else "Would grant"
    print(f"{verb} ({len(granted)}): {', '.join(granted)}")
    print(f"Already had access ({len(already)}): {', '.join(already)}")
    print(f"Failed ({len(failed)}):")
    for name, error in failed:
        print(f"  {name}: {error}")


if __name__ == "__main__":
    main()
