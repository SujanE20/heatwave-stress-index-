"use client";

import type { ComponentProps } from "react";
import HyperlocalMapInner from "./HyperlocalMapInner";

export default function HyperlocalMap(props: ComponentProps<typeof HyperlocalMapInner>) {
  return <HyperlocalMapInner {...props} />;
}
