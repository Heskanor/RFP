import React from "react";
import ProjectHeader from "../components/ProjectHeader";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem
} from "../components/ui/select";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "../components/ui/dialog";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "../components/ui/tabs";
import ExactRfpModal from "../components/ExactRfpModal";
const img = "/assets/logo-light.svg";
const img1 = "/assets/logo-dark.svg";
const img2 = "/assets/img2.png";

const rfpProjects = [
  {
    id: "1",
    title: "ERP System Implimentation",
    description: "Looking for a comprehensive ERP solution for our manufacturing operations",
    vendors: 3,
    criteria: 5,
    created: "2024-01-15",
  },
];

export default function HomePage() {
  const [showNewProjectModal, setShowNewProjectModal] = React.useState(false);
  const [projectName, setProjectName] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [inputTab, setInputTab] = React.useState("upload");
  const [pastedText, setPastedText] = React.useState("");
  const [importUrl, setImportUrl] = React.useState("");

  function handleNewProjectFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files[0]) {
      // This function is no longer needed as RfpModal handles file input
    }
  }
  function handleNewProjectSubmit(e: React.FormEvent) {
    e.preventDefault();
    // TODO: handle new project creation logic here
    setShowNewProjectModal(false);
    // setNewProjectFile(null); // This line is no longer needed
    // setNewProjectName(""); // This line is no longer needed
    setPastedText("");
    setImportUrl("");
    setInputTab("upload");
  }

  return (
    <div className="bg-[#ffffff] box-border content-stretch flex flex-col items-start justify-start p-0 relative size-full min-h-screen">
      {/* Header */}
      <ProjectHeader />
      {/* Main Content */}
      <div className="bg-[#ffffff] relative rounded-lg shrink-0 w-full max-w-[1400px] mx-auto mt-8">
        <div className="flex flex-col items-center relative size-full">
          <div className="box-border content-stretch flex flex-col gap-4 items-center justify-start p-[32px] relative w-full">
            <h1 className="text-2xl font-bold mb-8 w-full">RFP Projects</h1>
            <div className="flex gap-4 w-full mb-4">
              <Input placeholder="Search projects" className="flex max-w-md " />
              <Select>
                <SelectTrigger className="min-w-[140px]">
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="open">Open</SelectItem>
                  <SelectItem value="closed">Closed</SelectItem>
                </SelectContent>
              </Select>
              <div className="flex flex-col gap-4 w-full h-full items-end">
                <ExactRfpModal
                  open={showNewProjectModal}
                  onClose={() => setShowNewProjectModal(false)}
                  mode="new"
                  projectName={projectName}
                  setProjectName={setProjectName}
                  file={file}
                  setFile={setFile}
                  rfpVersions={[]}
                  onSubmit={() => { setShowNewProjectModal(false); setProjectName(""); setFile(null); }}
                  loading={false}
                />
                <Button variant="outline" className="w-fit px-5 py-2 text-base font-semibold bg-white" onClick={() => setShowNewProjectModal(true)}>
                  New Project
                </Button>
              </div>
            </div>
            {rfpProjects.map((rfp) => (
              <a
                key={rfp.id}
                href="/buyer-project"
                className="block no-underline text-inherit border border-zinc-300 rounded-lg p-6 mb-6 w-full bg-white cursor-pointer hover:bg-zinc-50 transition"
              >
                <div className="font-bold text-xl mb-1">{rfp.title}</div>
                <div className="text-base mb-2">{rfp.description}</div>
                <div className="text-zinc-600 text-sm">
                  {rfp.vendors} Vendors &nbsp; {rfp.criteria} Criteria &nbsp; Created {rfp.created}
                </div>
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
