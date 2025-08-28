import React from "react";
import { Input } from "./ui/input";
const img = "/assets/logo-light.svg";
const img1 = "/assets/logo-dark.svg";
const img2 = "/assets/img2.png";

export default function ProjectHeader() {
  return (
    <div className="backdrop-blur-[2.85px] backdrop-filter bg-[#ffffff] shrink-0 sticky top-0 z-30 w-full px-8 py-3">
      <div className="absolute border-[0px_0px_1px] border-slate-300 border-solid inset-0 pointer-events-none" />
      <div className="flex flex-row items-center justify-between relative size-full">
        {/* Left: Logo */}
        <a href="/" className="box-border content-stretch flex flex-row gap-1 items-start justify-start p-0 relative shrink-0" style={{ textDecoration: 'none' }}>
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
        </a>
        {/* Right: Search and Avatar */}
        <div className="box-border content-stretch flex flex-row gap-2.5 items-center justify-end p-0 relative shrink-0">
          <div className="bg-[#ffffff] box-border content-stretch flex flex-row h-8 items-center justify-between px-3 py-1 relative rounded-md shrink-0 w-[300px] gap-2">
            <Input
              className="w-full placeholder:text-zinc-500"
              placeholder="Search anything..."
              type="text"
            />
            <div className="flex items-center gap-1 bg-neutral-50 rounded px-2 py-0.5 border border-zinc-200 text-xs text-zinc-500">
              <span className="inline-block"><img src={img1} alt="Command Icon" className="inline-block w-3 h-3 mr-1 align-middle" /></span>
              K
            </div>
          </div>
          <div className="relative rounded-[8234.47px] shrink-0 size-7">
            <div className="absolute bg-center bg-cover bg-no-repeat inset-0 rounded-[8234.47px]" style={{ backgroundImage: `url('${img2}')` }} />
          </div>
        </div>
      </div>
    </div>
  );
} 