from django.shortcuts import redirect
import logging

logger = logging.getLogger("shs_system.middleware")


class RoleBasedAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.debug(f"RoleBasedAccessMiddleware processing request: {request.path}")

        if request.user.is_authenticated:
            logger.debug(
                f"User authenticated: {request.user.username}, Role: {request.user.role}"
            )

            # Map path segments to allowed roles
            allowed_roles = {
                "admin-dashboard": ["admin", "superadmin"],
                "teacher-dashboard": ["teacher", "superadmin"],
                "student-dashboard": ["student", "superadmin"],
                "dashboard": ["admin", "teacher", "student", "superadmin"],
                "admin_dashboard": ["admin", "superadmin"],
                "teacher_dashboard": ["teacher", "superadmin"],
                "student_dashboard": ["student", "superadmin"],
            }

            # Extract the first part of the path after stripping slashes
            path = request.path.strip("/")
            path_parts = path.split("/")

            # Check if the first path part is in our allowed_roles dictionary
            if path_parts and path_parts[0] in allowed_roles:
                current_path = path_parts[0]
                user_role = request.user.role

                logger.debug(
                    f"Checking access: Path: {current_path}, User Role: {user_role}"
                )
                logger.debug(
                    f"Allowed roles for this path: {allowed_roles[current_path]}"
                )

                if user_role not in allowed_roles[current_path]:
                    logger.warning(
                        f"Access denied: {user_role} not allowed in {current_path}"
                    )
                    return redirect("login")  # Redirect unauthorized users
                else:
                    logger.debug(
                        f"Access granted to {current_path} for role {user_role}"
                    )

        response = self.get_response(request)
        return response
