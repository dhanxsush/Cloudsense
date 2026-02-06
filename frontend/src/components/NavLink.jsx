import { NavLink, NavLinkProps } from "react-router-dom";
import { forwardRef } from "react";
import { cn } from "@/lib/utils";
interface NavLinkCompatProps extends Omit {
  className?;
  activeClassName?;
  pendingClassName?;
}
const NavLink = forwardRef(
  ({ className, activeClassName, pendingClassName, to, ...props }, ref) => {
    return (
          cn(className, isActive && activeClassName, isPending && pendingClassName)
        }
        {...props}
      />
    );
  },
);
NavLink.displayName = "NavLink";
export { NavLink };
