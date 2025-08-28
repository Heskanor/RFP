import React from "react";

// Inline SVGs from buyer-project
const UploadIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 16V4m0 0l-4 4m4-4l4 4M4 20h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);
const EyeIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);
const CheckIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

export interface RfpVersion {
  name: string;
  date: string;
  time: string;
}

interface ExactRfpModalProps {
  open: boolean;
  onClose: () => void;
  mode: "new" | "update";
  projectName: string;
  setProjectName: (name: string) => void;
  file: File | null;
  setFile: (file: File | null) => void;
  rfpVersions: RfpVersion[];
  currentRfpVersion?: number;
  onVersionChange?: (idx: number) => void;
  onSubmit: (data: { file?: File | null; text?: string; url?: string; inputTab: string }) => void;
  loading?: boolean;
}

const ExactRfpModal: React.FC<ExactRfpModalProps> = ({
  open,
  onClose,
  mode,
  projectName,
  setProjectName,
  file,
  setFile,
  rfpVersions,
  currentRfpVersion = 0,
  onVersionChange,
  onSubmit,
  loading,
}) => {
  const [inputTab, setInputTab] = React.useState<'upload' | 'paste' | 'url'>('upload');
  const [text, setText] = React.useState("");
  const [url, setUrl] = React.useState("");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      file: inputTab === 'upload' ? file : undefined,
      text: inputTab === 'paste' ? text : undefined,
      url: inputTab === 'url' ? url : undefined,
      inputTab,
    });
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-[857px] relative flex flex-col border border-zinc-200 p-0">
        <button
          className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-900 text-2xl font-bold"
          onClick={onClose}
          aria-label="Close"
        >
          &times;
        </button>
        <div className="w-full flex flex-col items-center px-0 pt-0 pb-0">
          <div className="w-full flex flex-col gap-6 items-center justify-center pt-6 px-6">
            <div className="w-full flex flex-col gap-1.5 items-start">
              <div className="flex flex-row gap-2.5 items-center">
                <span className="font-semibold text-[16px] text-zinc-950">{mode === "update" ? "Update RFP" : "New Project"}</span>
              </div>
              <div className="flex flex-row gap-2.5 items-center w-full">
                <span className="text-[14px] text-zinc-500">Upload your new RFP file here, or click to browse.</span>
              </div>
            </div>
            <div className="bg-zinc-100 rounded-lg w-full">
              <div className="flex flex-row items-center w-full p-1 gap-2">
                <button
                  className={`flex-1 flex flex-col gap-2.5 items-center justify-center px-2 py-1 rounded-md shadow font-medium text-[14px] border ${inputTab === 'upload' ? 'bg-white text-zinc-950 border-zinc-200' : 'bg-zinc-100 text-zinc-500 border-transparent'}`}
                  onClick={() => setInputTab('upload')}
                  type="button"
                >
                  Upload PDF
                </button>
                <button
                  className={`flex-1 flex flex-col gap-2.5 h-7 items-center justify-center px-2 py-1 rounded-md font-medium text-[14px] border ${inputTab === 'paste' ? 'bg-white text-zinc-950 border-zinc-200 shadow' : 'bg-zinc-100 text-zinc-500 border-transparent'}`}
                  onClick={() => setInputTab('paste')}
                  type="button"
                >
                  Paste Text
                </button>
                <button
                  className={`flex-1 flex flex-col gap-2.5 h-7 items-center justify-center px-2 py-1 rounded-md font-medium text-[14px] border ${inputTab === 'url' ? 'bg-white text-zinc-950 border-zinc-200 shadow' : 'bg-zinc-100 text-zinc-500 border-transparent'}`}
                  onClick={() => setInputTab('url')}
                  type="button"
                >
                  Import from URL
                </button>
              </div>
            </div>
          </div>
          <form className="w-full flex flex-row gap-6 items-start justify-start p-6" onSubmit={handleSubmit}>
            {/* Left: Upload Area or Text/URL */}
            <div className="flex-1 flex flex-col gap-6 min-w-[0]">
              {inputTab === 'upload' && (
                <div className="bg-zinc-100 h-[212px] rounded-lg w-full flex flex-col items-center justify-center relative">
                  <div className="absolute border-2 border-dashed border-zinc-500 inset-0 pointer-events-none rounded-lg" />
                  <label htmlFor="update-rfp-upload" className="flex flex-col items-center justify-center cursor-pointer w-full h-full">
                    <div className="h-16 w-24 mb-2 flex items-center justify-center">
                      <UploadIcon />
                    </div>
                    <span className="text-zinc-500 text-[16px]">Click or drag files to upload</span>
                    <input
                      id="update-rfp-upload"
                      type="file"
                      onChange={handleFileChange}
                      className="hidden"
                      required={inputTab === "upload"}
                    />
                    {file && (
                      <span className="mt-2 text-zinc-900 font-medium text-sm">{file.name}</span>
                    )}
                  </label>
                </div>
              )}
              {inputTab === 'paste' && (
                <textarea
                  className="bg-zinc-100 h-[212px] rounded-lg w-full p-4 text-base border border-zinc-200 shadow-sm"
                  placeholder="Paste your RFP text here..."
                  value={text}
                  onChange={e => setText(e.target.value)}
                  required={inputTab === 'paste'}
                />
              )}
              {inputTab === 'url' && (
                <input
                  className="bg-zinc-100 h-12 rounded-lg w-full px-4 text-base border border-zinc-200 shadow-sm"
                  placeholder="Enter a URL to import RFP..."
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                  required={inputTab === 'url'}
                />
              )}
              <div className="flex flex-col gap-2.5 w-full">
                <span className="font-medium text-[14px] text-zinc-950">Project name</span>
                <input
                  className="bg-white h-9 rounded-md w-full px-3 border border-zinc-200 shadow-sm text-[16px] text-zinc-950 font-normal"
                  placeholder="Enter project name"
                  value={projectName}
                  onChange={e => setProjectName(e.target.value)}
                  required
                  disabled={mode === "update"}
                />
              </div>
            </div>
            {/* Right: RFP Versions */}
            <div className="flex-1 flex flex-col gap-4 min-w-[0]">
              <div className="flex items-center justify-between">
                <span className="font-medium text-[14px] text-zinc-950">RFP Versions</span>
                <span className="text-xs text-zinc-500">{rfpVersions.length > 0 ? `${rfpVersions.length} versions` : "No versions yet"}</span>
              </div>
              <div className="flex flex-col gap-4 w-full max-h-[300px] overflow-y-auto pr-1">
                {rfpVersions.length > 0 ? (
                  rfpVersions.map((rfp, idx) => (
                    <div key={idx} className={`rounded-md w-full flex flex-col shadow-sm border ${idx === currentRfpVersion ? 'bg-green-50 border-green-200' : 'bg-white border-zinc-200'}`}>
                      <div className="flex flex-row items-center justify-between px-2 py-1">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <span className="font-medium text-[14px] text-zinc-950 truncate">{rfp.name}</span>
                          {idx === currentRfpVersion && (
                            <span className="bg-green-100 text-green-800 text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap flex items-center gap-1">
                              <CheckIcon />
                              Current
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1">
                          <button type="button" className="p-1 hover:bg-zinc-100 rounded">
                            <EyeIcon />
                          </button>
                          {idx !== currentRfpVersion && onVersionChange && (
                            <button 
                              type="button" 
                              className="text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 px-2 py-1 rounded transition-colors font-medium"
                              onClick={() => onVersionChange(idx)}
                            >
                              Use this version
                            </button>
                          )}
                        </div>
                      </div>
                      <div className="flex flex-row text-xs text-zinc-500 justify-between px-2 pb-1">
                        <span>{rfp.date}</span>
                        <span>{rfp.time}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <span className="text-zinc-400 text-sm">No RFP versions uploaded yet.</span>
                )}
              </div>
            </div>
          </form>
          <div className="w-full flex flex-col items-center px-6 pb-6">
            <button
              type="submit"
              className="bg-zinc-950 hover:bg-zinc-800 text-neutral-50 font-medium text-[14px] rounded-md shadow px-4 py-2 w-full"
              onClick={handleSubmit}
              disabled={loading || (inputTab === 'upload' && !file) || (inputTab === 'paste' && !text) || (inputTab === 'url' && !url)}
            >
              {mode === "update" ? "Save changes" : "Create Project"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExactRfpModal; 