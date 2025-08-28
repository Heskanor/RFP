import React from "react";
import { Input } from "./ui/input";
const img = "/assets/logo-light.svg";
const img2 = "/assets/img2.png";

export default function Header() {
  return (
    <div className="backdrop-blur-[2.85px] backdrop-filter bg-[#ffffff] shrink-0 sticky top-0 z-30 w-full px-8 py-3">
      <div className="absolute border-[0px_0px_1px] border-slate-300 border-solid inset-0 pointer-events-none" />
      <div className="flex flex-row items-center justify-between relative size-full">
        {/* Left: Logo */}
        <div className="box-border content-stretch flex flex-row gap-1 items-start justify-start p-0 relative shrink-0">
          <div className="h-7 relative shrink-0 w-[25.55px]">
            <div className="absolute h-7 left-0 top-0 w-[25.55px]">
              <img alt="Cube5 Logo" className="block max-w-none size-full" src={img} />
            </div>
          </div>
          <div className="font-bold leading-[0] not-italic relative shrink-0 text-[18px] text-left text-nowrap text-zinc-950">
            <p className="block leading-[28px] whitespace-pre">Cube5</p>
          </div>
          <div className="box-border content-stretch flex flex-col gap-2.5 h-5 items-center justify-center p-0 relative rounded-[11763.5px] shrink-0 w-8">
            <div className="absolute border border-solid border-zinc-200 inset-0 pointer-events-none rounded-[11763.5px]" />
            <div className="box-border content-stretch flex flex-row gap-2.5 items-center justify-center p-0 relative shrink-0">
              <div className="font-semibold leading-[0] not-italic relative shrink-0 text-[8px] text-left text-nowrap text-zinc-950">
                <p className="block leading-[16px] whitespace-pre">Buyer</p>
              </div>
            </div>
          </div>
        </div>
        {/* Center: Search */}
        <div className="flex-1 flex justify-center px-8">
          <Input placeholder="Search projects" className="max-w-md" />
        </div>
        {/* Right: Avatar */}
        <div className="box-border content-stretch flex flex-row gap-2.5 items-center justify-end p-0 relative shrink-0">
          <div className="relative rounded-[8234.47px] shrink-0 size-7">
            <div className="absolute bg-center bg-cover bg-no-repeat inset-0 rounded-[8234.47px]" style={{ backgroundImage: `url('${img2}')` }} />
          </div>
          <div className="flex flex-col items-end">
            <span className="font-semibold text-sm text-zinc-950">John Smith</span>
            <span className="text-xs text-zinc-500">Procurement Manager</span>
          </div>
        </div>
      </div>
    </div>
  );
} 