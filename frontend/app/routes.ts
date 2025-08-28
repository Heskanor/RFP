import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("buyer-project", "routes/buyer-project.tsx"),
] satisfies RouteConfig;
