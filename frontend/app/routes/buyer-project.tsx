import React from "react";
import {
  useReactTable,
  getCoreRowModel,
  getExpandedRowModel,
  flexRender,
  createColumnHelper,
} from "@tanstack/react-table";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { DataTableFilter } from '../../components/data-table-filter/components/data-table-filter';
import { useDataTableFilters } from '../../components/data-table-filter/hooks/use-data-table-filters';
import { FilterIcon, PercentIcon, UserIcon } from 'lucide-react';
import { useChat } from '@ai-sdk/react';
// Image asset constants
const img2 = "/assets/img2.png";
const img = "/assets/logo-light.svg";
const img1 = "/assets/logo-dark.svg";
const img3 = "/assets/img3.svg";
const imgFrame = "/assets/imgFrame.svg";
const img4 = "/assets/img4.svg";
const img5 = "/assets/img5.svg";
const img6 = "/assets/img6.svg";
const img7 = "/assets/img7.svg";
const img8 = "/assets/img8.svg";
const img9 = "/assets/img9.svg";
const img10 = "/assets/img10.svg";
// Clear, readable icon imports from public/assets
// Icons are now inline SVG components for reliable loading

// Inline SVG components for reliable icon loading
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

type SubCriteria = {
  id: string;
  text: string;
  weight: string;
  scores: string[];
};

type TableRow = {
  id: string;
  title: string;
  weight: string;
  scores: string[];
  sub?: SubCriteria[];
};

/**
 * Vendor RFP scoring type
 * @typedef {Object} Vendor
 * @property {number} experienceAndCapabilities
 * @property {number} serviceApproachAndMethodology
 * @property {number} complianceAndRegulatoryAlignment
 * @property {number} sustainabilityAndDEICommitments
 * @property {number} costCompetitivenessAndValue
 * @property {number} innovationAndTechnologicalAdvancement
 * @property {number} [overallScore] - Computed weighted score (0-100)
 */

type Vendor = {
  experienceAndCapabilities: number;
  serviceApproachAndMethodology: number;
  complianceAndRegulatoryAlignment: number;
  sustainabilityAndDEICommitments: number;
  costCompetitivenessAndValue: number;
  innovationAndTechnologicalAdvancement: number;
  overallScore?: number;
};

/**
 * Computes weighted RFP scores for vendors.
 * @param vendors Array of vendor objects
 * @returns Array of vendors with overallScore property
 */
function computeWeightedRFPScoring(vendors: Vendor[]): Vendor[] {
  const weights = {
    experienceAndCapabilities: 0.20,
    serviceApproachAndMethodology: 0.20,
    complianceAndRegulatoryAlignment: 0.15,
    sustainabilityAndDEICommitments: 0.15,
    costCompetitivenessAndValue: 0.15,
    innovationAndTechnologicalAdvancement: 0.15,
  };
  return vendors.map(vendor => {
    const overallScore =
      vendor.experienceAndCapabilities * weights.experienceAndCapabilities +
      vendor.serviceApproachAndMethodology * weights.serviceApproachAndMethodology +
      vendor.complianceAndRegulatoryAlignment * weights.complianceAndRegulatoryAlignment +
      vendor.sustainabilityAndDEICommitments * weights.sustainabilityAndDEICommitments +
      vendor.costCompetitivenessAndValue * weights.costCompetitivenessAndValue +
      vendor.innovationAndTechnologicalAdvancement * weights.innovationAndTechnologicalAdvancement;
    return { ...vendor, overallScore };
  });
}

// Example dataset
const exampleVendors: Vendor[] = [
  {
    experienceAndCapabilities: 80,
    serviceApproachAndMethodology: 90,
    complianceAndRegulatoryAlignment: 85,
    sustainabilityAndDEICommitments: 70,
    costCompetitivenessAndValue: 75,
    innovationAndTechnologicalAdvancement: 95,
  },
  {
    experienceAndCapabilities: 60,
    serviceApproachAndMethodology: 70,
    complianceAndRegulatoryAlignment: 65,
    sustainabilityAndDEICommitments: 80,
    costCompetitivenessAndValue: 85,
    innovationAndTechnologicalAdvancement: 75,
  },
];

const scoredVendors = computeWeightedRFPScoring(exampleVendors);
console.log('Weighted RFP Scoring Results:', scoredVendors);

// Simple unit test/assertion
const expectedScore =
  80 * 0.2 + 90 * 0.2 + 85 * 0.15 + 70 * 0.15 + 75 * 0.15 + 95 * 0.15;
if (Math.abs(scoredVendors[0].overallScore! - expectedScore) > 0.0001) {
  throw new Error('Weighted RFP scoring calculation failed!');
}

function getRandomPercent() {
  return `${Math.floor(Math.random() * 41) + 60}%`;
}

function fillVendorScores(row: TableRow): TableRow {
  return {
    ...row,
    scores: row.scores.map((val: string) => val === '-' ? getRandomPercent() : val),
    sub: row.sub ? row.sub.map((subRow: SubCriteria) => ({
      ...subRow,
      scores: subRow.scores.map((val: string) => val === '-' ? getRandomPercent() : val),
    })) : undefined,
  };
}

const initialTableData: TableRow[] = [
  {
    id: "5.1",
    title: "Experience and Capabilities",
    weight: "20%",
    scores: ["-", "-", "-", "-", "-"],
    sub: [
      { id: "5.1.1", text: "5.1.1. Provider's demonstrated ability to deliver SCaaS in comparable settings will be assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.1.2", text: "5.1.2. Specific experience within the EU or Scandinavian regions will be favorably considered.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.1.3", text: "5.1.3. Telecommunications industry experience will be evaluated as a significant advantage.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.1.4", text: "5.1.4. Provider's track record of successful implementations of similar scale will be reviewed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.1.5", text: "5.1.5. Strength and relevance of client references will be carefully assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.1.6", text: "5.1.6. Provider's financial stability and organizational capacity will be evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.1.7", text: "5.1.7. Geographic coverage and operational capabilities across Europe will be considered.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.1.8", text: "5.1.8. Provider's experience with mission-critical supply chains will be highly valued.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.1.9", text: "5.1.9. Technology capabilities and digital transformation experience will be assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.1.10", text: "5.1.10. Provider's demonstrated ability to drive measurable improvements will be evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
    ],
  },
  {
    id: "5.2",
    title: "Service Approach and Methodology",
    weight: "20%",
    scores: ["-", "-", "-", "-", "-"],
    sub: [
      { id: "5.2.1", text: "5.2.1. Completeness and clarity of the proposed service delivery approach will be evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.2.2", text: "5.2.2. Alignment with NeoTelc's operational requirements will be carefully assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.2.3", text: "5.2.3. Provider's approach to service integration and end-to-end management will be considered.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.2.4", text: "5.2.4. Scalability and flexibility of the proposed solution will be evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.2.5", text: "5.2.5. Provider's methodology for continuous improvement will be assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.2.6", text: "5.2.6. Innovation capability and approach to driving operational excellence will be considered.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.2.7", text: "5.2.7. Provider's risk management approach will be evaluated for comprehensiveness.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.2.8", text: "5.2.8. Quality of the implementation and transition methodology will be assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.2.9", text: "5.2.9. Provider's approach to performance measurement and reporting will be considered.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.2.10", text: "5.2.10. Feasibility and pragmatism of the proposed approach will be carefully evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
    ],
  },
  {
    id: "5.3",
    title: "Compliance and Regulatory Alignment",
    weight: "15%",
    scores: ["-", "-", "-", "-", "-"],
    sub: [
      { id: "5.3.1", text: "5.3.1. Compliance with NeoTelc's corporate standards will be rigorously reviewed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.3.2", text: "5.3.2. Adherence to industry regulations will be carefully assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.3.3", text: "5.3.3. Provider's approach to environmental and ethical guidelines will be evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.3.4", text: "5.3.4. Quality and environmental management certifications will be considered.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.3.5", text: "5.3.5. Provider's data protection and information security practices will be assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.3.6", text: "5.3.6. Compliance with labor laws and workplace regulations will be reviewed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.3.7", text: "5.3.7. Provider's approach to regulatory monitoring and updates will be evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.3.8", text: "5.3.8. Ethical business practices and anti-corruption policies will be assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.3.9", text: "5.3.9. Provider's compliance track record and any historical issues will be considered.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.3.10", text: "5.3.10. Quality of compliance documentation and evidence will be evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
    ],
  },
  {
    id: "5.4",
    title: "Sustainability and DEI Commitments",
    weight: "15%",
    scores: ["-", "-", "-", "-", "-"],
    sub: [
      { id: "5.4.1", text: "5.4.1. Strength and maturity of the provider's sustainability programs will be assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.4.2", text: "5.4.2. Provider's carbon reduction initiatives and environmental impact strategies will be evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.4.3", text: "5.4.3. Diversity, Equity, and Inclusion commitments will be carefully reviewed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.4.4", text: "5.4.4. Provider's ability to provide measurable impact metrics will be considered advantageous.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.4.5", text: "5.4.5. Verifiable sustainability and DEI initiatives will be highly valued.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.4.6", text: "5.4.6. Alignment with NeoTelc's own sustainability goals will be evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.4.7", text: "5.4.7. Provider's approach to sustainable supply chain practices will be assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.4.8", text: "5.4.8. Community engagement and social responsibility initiatives will be considered.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.4.9", text: "5.4.9. Provider's circular economy and waste reduction programs will be evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.4.10", text: "5.4.10. Quality and comprehensiveness of sustainability reporting will be assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
    ],
  },
  {
    id: "5.5",
    title: "Cost Competitiveness and Value",
    weight: "15%",
    scores: ["-", "-", "-", "-", "-"],
    sub: [
      { id: "5.5.1", text: "5.5.1. Overall value proposition rather than lowest price will be the primary consideration.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.5.2", text: "5.5.2. Cost transparency and detailed breakdown will be positively evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.5.3", text: "5.5.3. Provider's approach to cost optimization over time will be assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.5.4", text: "5.5.4. Value-added services included in the pricing model will be considered.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.5.5", text: "5.5.5. Performance-based pricing components will be viewed favorably.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.5.6", text: "5.5.6. Provider's approach to shared savings and continuous improvement will be evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.5.7", text: "5.5.7. Total cost of ownership over the contract duration will be carefully assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.5.8", text: "5.5.8. Financial benefits and return on investment projections will be considered.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.5.9", text: "5.5.9. Provider's financial models and assumptions will be critically evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.5.10", text: "5.5.10. Cost risk mitigation strategies will be assessed for effectiveness.", weight: "", scores: ["-", "-", "-", "-", "-"] },
    ],
  },
  {
    id: "5.6",
    title: "Innovation and Technological Advancement",
    weight: "15%",
    scores: ["-", "-", "-", "-", "-"],
    sub: [
      { id: "5.6.1", text: "5.6.1. Provider's technology capabilities and digital supply chain solutions will be evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.6.2", text: "5.6.2. Innovation roadmap and approach to continuous technological improvement will be assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.6.3", text: "5.6.3. Provider's experience with advanced analytics and data-driven decision making will be considered.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.6.4", text: "5.6.4. Integration capabilities with NeoTelc's systems will be carefully evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.6.5", text: "5.6.5. Provider's approach to emerging technologies such as AI, IoT, and blockchain will be assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.6.6", text: "5.6.6. Technology architecture and infrastructure robustness will be considered.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.6.7", text: "5.6.7. Provider's approach to cybersecurity and data protection will be evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.6.8", text: "5.6.8. Innovation culture and successful implementation of innovative solutions will be assessed.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.6.9", text: "5.6.9. Provider's investment in research and development will be considered.", weight: "", scores: ["-", "-", "-", "-", "-"] },
      { id: "5.6.10", text: "5.6.10. Alignment of technological capabilities with NeoTelc's digital transformation goals will be evaluated.", weight: "", scores: ["-", "-", "-", "-", "-"] },
    ],
  },
].map(fillVendorScores);

const getSubRows = (row: TableRow): TableRow[] =>
  row.sub?.map(sub => ({
    id: sub.id,
    title: sub.text,
    weight: sub.weight,
    scores: sub.scores,
  })) || [];

function calculateOverallScore(sectionScores: number[], weights: number[]): number {
  const totalWeight = weights.reduce((sum, w) => sum + w, 0);
  if (totalWeight === 0) return 0;
  const raw = sectionScores
    .map((score, i) => score * weights[i])
    .reduce((sum, x) => sum + x, 0) / totalWeight;
  return Math.round(raw * 10) / 10; // one decimal place
}

// 1. Add Icon component at the top of the file (typed)
type IconName = 'doc' | 'compare' | 'chevron-right' | 'external-link';
interface IconProps {
  name: IconName;
  className?: string;
}
const ICONS: Record<IconName, React.ReactElement> = {
  doc: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="3" y="2" width="10" height="12" rx="2" fill="#F3F4F6" stroke="#D1D5DB" strokeWidth="1.2"/>
      <rect x="5" y="5" width="6" height="1" rx="0.5" fill="#9CA3AF"/>
      <rect x="5" y="7" width="6" height="1" rx="0.5" fill="#9CA3AF"/>
      <rect x="5" y="9" width="4" height="1" rx="0.5" fill="#9CA3AF"/>
    </svg>
  ),
  compare: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="3" width="4" height="10" rx="1" fill="#F3F4F6" stroke="#D1D5DB" strokeWidth="1.2"/>
      <rect x="10" y="3" width="4" height="10" rx="1" fill="#F3F4F6" stroke="#D1D5DB" strokeWidth="1.2"/>
      <rect x="7" y="6" width="2" height="4" rx="1" fill="#2563EB"/>
    </svg>
  ),
  'chevron-right': (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M6 4l4 4-4 4" stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  'external-link': (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M7 9l4-4m0 0H9m2-2v4" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      <rect x="3" y="7" width="6" height="6" rx="1" stroke="#6B7280" strokeWidth="1.2"/>
    </svg>
  ),
};
const Icon: React.FC<IconProps> = ({ name, className }) => <span className={className}>{ICONS[name]}</span>;

// 2. Refactor Bid Details modal (lines 824-1023) to use shadcn/ui components instead of Tailwind classes
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
  DialogOverlay,
} from "../components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";

// Reference icon for the popup table column widths
const ReferenceIcon = () => (
  <svg width="24" height="25" viewBox="0 0 24 25" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M19.9805 3.49016C19.9432 3.49134 19.906 3.4946 19.8691 3.49993H15C14.8675 3.49805 14.7359 3.52254 14.613 3.57195C14.49 3.62136 14.3781 3.69472 14.2837 3.78777C14.1893 3.88081 14.1144 3.99169 14.0632 4.11394C14.0121 4.2362 13.9858 4.3674 13.9858 4.49993C13.9858 4.63245 14.0121 4.76366 14.0632 4.88591C14.1144 5.00817 14.1893 5.11904 14.2837 5.21209C14.3781 5.30513 14.49 5.37849 14.613 5.42791C14.7359 5.47732 14.8675 5.5018 15 5.49993H17.5859L8.29297 14.7929C8.197 14.885 8.12037 14.9954 8.06759 15.1175C8.0148 15.2397 7.98692 15.3711 7.98556 15.5041C7.98421 15.6372 8.00942 15.7692 8.0597 15.8923C8.10999 16.0155 8.18435 16.1274 8.27843 16.2215C8.37251 16.3156 8.48442 16.3899 8.6076 16.4402C8.73077 16.4905 8.86275 16.5157 8.99579 16.5144C9.12883 16.513 9.26026 16.4851 9.38239 16.4323C9.50452 16.3796 9.61489 16.3029 9.70703 16.207L19 6.91399V9.49993C18.9981 9.63244 19.0226 9.764 19.072 9.88697C19.1214 10.0099 19.1948 10.1219 19.2878 10.2162C19.3809 10.3106 19.4918 10.3855 19.614 10.4367C19.7363 10.4878 19.8675 10.5142 20 10.5142C20.1325 10.5142 20.2637 10.4878 20.386 10.4367C20.5082 10.3855 20.6191 10.3106 20.7122 10.2162C20.8052 10.1219 20.8786 10.0099 20.928 9.88697C20.9774 9.764 21.0019 9.63244 21 9.49993V4.62688C21.0199 4.48291 21.0082 4.33632 20.9657 4.19733C20.9232 4.05834 20.8509 3.93029 20.7538 3.82209C20.6568 3.71389 20.5373 3.62814 20.4038 3.57081C20.2702 3.51349 20.1258 3.48597 19.9805 3.49016ZM5 3.49993C3.90694 3.49993 3 4.40687 3 5.49993V19.4999C3 20.593 3.90694 21.4999 5 21.4999H19C20.0931 21.4999 21 20.593 21 19.4999V13.4999C21.0019 13.3674 20.9774 13.2359 20.928 13.1129C20.8786 12.9899 20.8052 12.878 20.7122 12.7836C20.6191 12.6893 20.5082 12.6143 20.386 12.5632C20.2637 12.512 20.1325 12.4857 20 12.4857C19.8675 12.4857 19.7363 12.512 19.614 12.5632C19.4918 12.6143 19.3809 12.6893 19.2878 12.7836C19.1948 12.878 19.1214 12.9899 19.072 13.1129C19.0226 13.2359 18.9981 13.3674 19 13.4999V19.4999H5V5.49993H11C11.1325 5.5018 11.2641 5.47732 11.387 5.42791C11.51 5.37849 11.6219 5.30513 11.7163 5.21209C11.8107 5.11904 11.8856 5.00817 11.9368 4.88591C11.9879 4.76366 12.0142 4.63245 12.0142 4.49993C12.0142 4.3674 11.9879 4.2362 11.9368 4.11394C11.8856 3.99169 11.8107 3.88081 11.7163 3.78777C11.6219 3.69472 11.51 3.62136 11.387 3.57195C11.2641 3.52254 11.1325 3.49805 11 3.49993H5Z" fill="black"/>
  </svg>
);

// View bid document icon for the button
const ViewBidIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M2 6.66671C2 4.15271 2 2.89537 2.78133 2.11471C3.56267 1.33404 4.81933 1.33337 7.33333 1.33337H8.66667C11.1807 1.33337 12.438 1.33337 13.2187 2.11471C13.9993 2.89604 14 4.15271 14 6.66671V9.33337C14 11.8474 14 13.1047 13.2187 13.8854C12.4373 14.666 11.1807 14.6667 8.66667 14.6667H7.33333C4.81933 14.6667 3.562 14.6667 2.78133 13.8854C2.00067 13.104 2 11.8474 2 9.33337V6.66671Z" stroke="black"/>
    <path d="M5.3335 6.66675H10.6668M5.3335 9.33341H8.66683" stroke="black" strokeLinecap="round"/>
  </svg>
);

// Compare with another icon for the button
const CompareIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M8.6665 2.66671H3.99984C3.64622 2.66671 3.30708 2.80718 3.05703 3.05723C2.80698 3.30728 2.6665 3.64642 2.6665 4.00004V12C2.6665 12.3537 2.80698 12.6928 3.05703 12.9428C3.30708 13.1929 3.64622 13.3334 3.99984 13.3334H8.6665M11.3332 2.66671H11.9998C12.3535 2.66671 12.6926 2.80718 12.9426 3.05723C13.1927 3.30728 13.3332 3.64642 13.3332 4.00004V4.66671M13.3332 11.3334V12C13.3332 12.3537 13.1927 12.6928 12.9426 12.9428C12.6926 13.1929 12.3535 13.3334 11.9998 13.3334H11.3332M13.3332 7.33337V8.66671M7.99984 1.33337V14.6667" stroke="black" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

// --- Add at the top of BuyerProject (after imports) ---
type BidDetailsColKey = 'criteria' | 'score' | 'justification' | 'reference';
interface BidDetailsColWidths {
  [key: string]: number;
  criteria: number;
  score: number;
  justification: number;
  reference: number;
}
const BID_DETAILS_DEFAULT_WIDTHS: BidDetailsColWidths = {
  criteria: 200,
  score: 100,
  justification: 300,
  reference: 120,
};
// --- existing code ...
import ProjectHeader from "../components/ProjectHeader";
// ... existing code ...
export default function BuyerProject() {
  const [data, setData] = React.useState<TableRow[]>(initialTableData);
  const [expanded, setExpanded] = React.useState<{}>({});
  const [searchTerm, setSearchTerm] = React.useState('');
  // Section weights are now controlled in data state only
  // Upload modal state
  const [showUploadModal, setShowUploadModal] = React.useState(false);
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  }
  function handleUploadSubmit(e: React.FormEvent) {
    e.preventDefault();
    // TODO: handle file upload logic here
    setShowUploadModal(false);
    setSelectedFile(null);
  }
  // Update RFP modal state
  const [showUpdateRfpModal, setShowUpdateRfpModal] = React.useState(false);
  const [updateRfpFile, setUpdateRfpFile] = React.useState<File | null>(null);
  const [projectName, setProjectName] = React.useState("ERP System Implimentation");
  const rfpVersions = [
    {name:'Existing RFP v2.pdf',date:'22/06/2025',time:'12:00'},
    {name:'Existing RFP v1.pdf',date:'15/05/2025',time:'10:30'},
    {name:'Existing RFP draft.pdf',date:'01/05/2025',time:'09:00'}
  ];
  const [versionChangeMessage, setVersionChangeMessage] = React.useState<string | null>(null);
  // Context menu and bid details modal state
  const [contextMenu, setContextMenu] = React.useState<{ x: number; y: number; rowIdx: number; colIdx: number } | null>(null);
  const [showBidDetails, setShowBidDetails] = React.useState(false);
  const [selectedBid, setSelectedBid] = React.useState<{ vendor: string; value: string; row: TableRow } | null>(null);
  function handleUpdateRfpFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files[0]) {
      setUpdateRfpFile(e.target.files[0]);
    }
  }
  function handleUpdateRfpSubmit(e: React.FormEvent) {
    e.preventDefault();
    // TODO: handle update RFP file upload logic here
    setShowUpdateRfpModal(false);
    setUpdateRfpFile(null);
  }

  // Helper to update weight for main or sub row
  const handleWeightChange = React.useCallback((rowId: string, value: string) => {
    setData(prevData =>
      prevData.map(row => {
        if (row.id === rowId) {
          return { ...row, weight: value };
        } else if (row.sub) {
          return {
            ...row,
            sub: row.sub.map(subRow =>
              subRow.id === rowId ? { ...subRow, weight: value } : subRow
            ),
          };
        }
        return row;
      })
    );
  }, []);

  function handleVersionChange(newVersionIndex: number) {
    setVersionChangeMessage(`Switched to ${[{name:'Existing RFP v2.pdf',date:'22/06/2025',time:'12:00'},{name:'Existing RFP v1.pdf',date:'15/05/2025',time:'10:30'},{name:'Existing RFP draft.pdf',date:'01/05/2025',time:'09:00'}][newVersionIndex].name}`);
    setTimeout(() => setVersionChangeMessage(null), 3000); // Clear message after 3 seconds
  }

const columnHelper = createColumnHelper<TableRow>();
  // Move these above columns definition
  const vendorColumnIds = [
    'LangeTech',
    'Best Pacific',
    'KMNM',
    'Bhilosa',
    'Tianhai Lace',
  ];
  const pinnedColumnIds = ['title', 'weight'];
  const allColumnIds = [...pinnedColumnIds, ...vendorColumnIds];
  const [columnOrder, setColumnOrder] = React.useState(allColumnIds);
  const columns = React.useMemo(() => [
  columnHelper.accessor("title", {
    header: () => "Evaluation Criteria",
    cell: ({ row, getValue }) => {
        const canExpand = row.getCanExpand && row.getCanExpand();
        const isExpanded = row.getIsExpanded && row.getIsExpanded();
        return (
          <span className="font-medium text-sm leading-5 text-zinc-950 flex items-center gap-2">
            {canExpand && (
              <svg
                className={`transition-transform duration-200 w-4 h-4 ${isExpanded ? 'rotate-90' : ''}`}
                viewBox="0 0 16 16"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
            {getValue()}
          </span>
        );
    },
      size: typeof window !== 'undefined' ? Math.floor(window.innerWidth * 0.4) : 400,
      minSize: 200,
      maxSize: 800,
  }),
  columnHelper.accessor("weight", {
    header: () => (
      <span>Weight</span>
    ),
    cell: ({ row, getValue }) => {
      // Use the same weight input for both main and sub-rows
      const [inputValue, setInputValue] = React.useState<string>(() => {
        const val = parseInt(getValue() || '');
        return isNaN(val) ? '' : String(val);
      });
      React.useEffect(() => {
        const val = parseInt(getValue() || '');
        setInputValue(isNaN(val) ? '' : String(val));
      }, [getValue()]);
      const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        if (val === '' || /^\d{0,3}$/.test(val)) {
          setInputValue(val);
        }
      };
      const handleInputBlur = () => {
        let num = parseInt(inputValue);
        if (isNaN(num)) {
          handleWeightChange(row.original.id, '');
          setInputValue('');
        } else {
          num = Math.max(0, Math.min(100, Math.round(num / 5) * 5));
          handleWeightChange(row.original.id, num + '%');
        }
      };
      return (
        <div className="relative flex items-center w-full h-full px-2">
          <button
            type="button"
            className="px-2 py-1 text-xs font-bold text-zinc-500 hover:text-zinc-900 focus:outline-none"
            onClick={(e: React.MouseEvent<HTMLButtonElement>) => {
              e.stopPropagation();
              let current = parseInt(inputValue || '0') || 0;
              let next = Math.max(0, current - 5);
              handleWeightChange(row.original.id, next + '%');
              setInputValue(String(next));
            }}
            tabIndex={-1}
          >
            −
          </button>
          <input
            type="number"
            min="0"
            max="100"
            step="5"
            className="flex-1 border rounded-md px-2 py-1 font-medium text-xs leading-4 text-zinc-950 bg-white focus:outline-none focus:ring-2 focus:ring-teal-600 text-center appearance-none hide-number-arrows mx-2 pr-8"
            value={inputValue}
            onChange={handleInputChange}
            onBlur={handleInputBlur}
            onClick={e => e.stopPropagation()}
            onFocus={e => e.stopPropagation()}
            style={{ MozAppearance: 'textfield' }}
          />
          <span className="absolute right-12 text-xs text-zinc-400 pointer-events-none" style={{paddingLeft: '8px'}}>%</span>
          <button
            type="button"
            className="px-2 py-1 text-xs font-bold text-zinc-500 hover:text-zinc-900 focus:outline-none"
            onClick={(e: React.MouseEvent<HTMLButtonElement>) => {
              e.stopPropagation();
              let current = parseInt(inputValue || '0') || 0;
              let next = Math.min(100, current + 5);
              handleWeightChange(row.original.id, next + '%');
              setInputValue(String(next));
            }}
            tabIndex={-1}
          >
            +
          </button>
        </div>
      );
    },
  }),
  ...vendorColumnIds.map((vendorId, vendorIdx) =>
    columnHelper.accessor((row) => row.scores[vendorIdx], {
      id: vendorId,
      header: () => vendorId,
      cell: ({ row, getValue }) => {
        const value = getValue();
        // For sub-criteria, use sub.text as justification; for main, use a placeholder
        let justification = '';
        if (row.depth > 0 && (row.original as any).text) {
          justification = (row.original as any).text;
        } else {
          justification = 'No justification provided.';
        }
        return (
          <div
            className="relative w-full h-full cursor-pointer flex items-center gap-1"
            onContextMenu={e => {
              e.preventDefault();
              setContextMenu({ x: e.pageX, y: e.pageY, rowIdx: row.index, colIdx: vendorIdx });
              setSelectedBid({ vendor: vendorId, value, row: row.original });
            }}
          >
            <span>{value}</span>
            <Tooltip text={justification}>
              <span style={{ display: 'inline-flex', alignItems: 'center', cursor: 'help', marginLeft: 4 }}>
                <svg width="14" height="14" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="10" fill="#e5e7eb"/><text x="50%" y="55%" textAnchor="middle" fill="#6366f1" fontSize="12" fontWeight="bold" dy=".3em">?</text></svg>
              </span>
            </Tooltip>
            {/* Context menu (only show for this cell) */}
            {contextMenu && contextMenu.rowIdx === row.index && contextMenu.colIdx === vendorIdx && (
              <div
                className="fixed z-50 bg-white border border-zinc-200 rounded shadow-lg py-1 px-0.5 min-w-[140px] text-sm text-zinc-950"
                style={{ left: contextMenu.x, top: contextMenu.y }}
              >
                <button
                  className="w-full text-left px-4 py-2 hover:bg-zinc-100 rounded"
                  onClick={() => {
                    setShowBidDetails(true);
                    setContextMenu(null);
                  }}
                >
                  Bid Details
                </button>
              </div>
            )}
          </div>
        );
      },
    })
  ),
  ], [handleWeightChange, contextMenu]);

  // Define columnsConfig for filtering
  // Helper to get unique options for a vendor column
  function getVendorOptions(idx: number) {
    const values = Array.from(new Set(data.flatMap(row => {
      if (row.scores[idx]) return [row.scores[idx]];
      if (row.sub) return row.sub.map(sub => sub.scores[idx]).filter(Boolean);
      return [];
    })));
    return values.map(v => ({ label: v, value: v }));
  }

  const columnsConfig = [
    {
      id: 'title',
      accessor: (row: TableRow) => row.title,
      displayName: 'Evaluation Criteria',
      icon: FilterIcon,
      type: 'text',
    },
    {
      id: 'weight',
      accessor: (row: TableRow) => row.weight,
      displayName: 'Weight',
      icon: PercentIcon,
      type: 'text',
    },
    { id: 'LangeTech', accessor: (row: TableRow) => row.scores[0], displayName: 'LangeTech', icon: UserIcon, type: 'option', options: getVendorOptions(0) },
    { id: 'Best Pacific', accessor: (row: TableRow) => row.scores[1], displayName: 'Best Pacific', icon: UserIcon, type: 'option', options: getVendorOptions(1) },
    { id: 'KMNM', accessor: (row: TableRow) => row.scores[2], displayName: 'KMNM', icon: UserIcon, type: 'option', options: getVendorOptions(2) },
    { id: 'Bhilosa', accessor: (row: TableRow) => row.scores[3], displayName: 'Bhilosa', icon: UserIcon, type: 'option', options: getVendorOptions(3) },
    { id: 'Tianhai Lace', accessor: (row: TableRow) => row.scores[4], displayName: 'Tianhai Lace', icon: UserIcon, type: 'option', options: getVendorOptions(4) },
  ];

  // Use DataTableFilter hook
  const {
    columns: filterColumns,
    filters,
    actions,
    strategy,
  } = useDataTableFilters({
    strategy: 'client',
    data,
    columnsConfig,
  });

  // Filter data using the filterColumns (client-side filtering)
  const filteredData = data.filter((row) => {
    // For each filter, check if the row matches
    return filters.every((filter) => {
      const col = columnsConfig.find((c) => c.id === filter.columnId);
      if (!col) return true;
      const value = col.accessor(row);
      // Simple contains logic for text
      if (filter.type === 'text') {
        return filter.values.length === 0 || filter.values.some((v) => String(value).toLowerCase().includes(String(v).toLowerCase()));
      }
      return true;
    });
  });

  const table = useReactTable<TableRow>({
    data: filteredData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    state: { expanded, columnOrder },
    onExpandedChange: setExpanded,
    getSubRows,
    columnResizeMode: 'onChange',
    onColumnOrderChange: setColumnOrder,
  });

  // DnD logic for vendor columns
  function DraggableTh({ header, index, moveColumn }: { header: any, index: number, moveColumn: (dragIndex: number, hoverIndex: number) => void }) {
    const id = header.column.id;
    const isDraggable = vendorColumnIds.includes(id);
    const [{ isDragging }, drag] = useDrag({
      type: 'COLUMN',
      item: { id, index },
      canDrag: isDraggable,
      collect: (monitor) => ({ isDragging: monitor.isDragging() }),
    });
    const [, drop] = useDrop({
      accept: 'COLUMN',
      canDrop: (item) => isDraggable,
      hover: (item: any) => {
        if (!isDraggable || item.index === index) return;
        moveColumn(item.index, index);
        item.index = index;
      },
    });
    const thRef = React.useRef<HTMLTableHeaderCellElement>(null);
    React.useEffect(() => {
      if (isDraggable && thRef.current) {
        drag(drop(thRef.current));
      }
    }, [isDraggable, drag, drop]);
    return (
      <th
        className={`px-2 py-2 text-left relative group font-medium text-sm leading-5 text-zinc-950 ${index > 0 ? 'border-l border-zinc-200' : ''}`}
        style={{ width: header.getSize(), opacity: isDragging ? 0.5 : 1 }}
      >
        <div className="flex flex-row items-center justify-start gap-2">
          <div ref={isDraggable ? thRef : undefined} className={`flex items-center justify-center w-5 h-5 ${isDraggable ? 'cursor-move' : ''}`}>
            {isDraggable && (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="5" cy="4" r="1" fill="#A1A1AA" />
                <circle cx="5" cy="8" r="1" fill="#A1A1AA" />
                <circle cx="5" cy="12" r="1" fill="#A1A1AA" />
                <circle cx="11" cy="4" r="1" fill="#A1A1AA" />
                <circle cx="11" cy="8" r="1" fill="#A1A1AA" />
                <circle cx="11" cy="12" r="1" fill="#A1A1AA" />
              </svg>
            )}
          </div>
          {flexRender(header.column.columnDef.header, header.getContext())}
        </div>
        {header.column.getCanResize() && (
          <div
            onMouseDown={header.getResizeHandler()}
            onTouchStart={header.getResizeHandler()}
            className="absolute right-0 top-0 h-full w-2 cursor-col-resize group-hover:bg-transparent transition-colors"
            style={{ zIndex: 1 }}
          />
        )}
        {isDraggable && (
          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-2 h-6 bg-gray-200 rounded cursor-move opacity-60 group-hover:opacity-100" />
        )}
      </th>
    );
  }

  // Move vendor columns in columnOrder
  const moveColumn = (dragIndex: number, hoverIndex: number) => {
    const pinned = columnOrder.slice(0, pinnedColumnIds.length);
    const vendors = columnOrder.slice(pinnedColumnIds.length);
    const dragCol = vendors[dragIndex - pinnedColumnIds.length];
    vendors.splice(dragIndex - pinnedColumnIds.length, 1);
    vendors.splice(hoverIndex - pinnedColumnIds.length, 0, dragCol);
    setColumnOrder([...pinned, ...vendors]);
  };

  // Generate random overall scores for vendors
  const overallScores = React.useMemo(() =>
    Array(5).fill(0).map(() => getRandomPercent()),
    []
  );

  // Helper to close context menu
  React.useEffect(() => {
    const closeMenu = () => setContextMenu(null);
    window.addEventListener('click', closeMenu);
    return () => window.removeEventListener('click', closeMenu);
  }, []);

  const [scoreDetailsExpandedRows, setScoreDetailsExpandedRows] = React.useState<string[]>([]);

  // Blade (side panel) state for Ask Anything chat
  const [showBlade, setShowBlade] = React.useState(false);

  // --- Add state for bid details popup table column widths ---
  const [bidDetailsColWidths, setBidDetailsColWidths] = React.useState<BidDetailsColWidths>(BID_DETAILS_DEFAULT_WIDTHS);
  const bidDetailsColOrder = [
    { key: 'criteria' as BidDetailsColKey, label: 'Evaluation Criteria' },
    { key: 'score' as BidDetailsColKey, label: 'Weighted Score' },
    { key: 'justification' as BidDetailsColKey, label: 'Justification' },
    { key: 'reference' as BidDetailsColKey, label: 'Reference' },
  ];
  // --- Resizing logic for bid details popup table ---
  const resizingCol = React.useRef<BidDetailsColKey | null>(null);
  const startX = React.useRef(0);
  const startWidth = React.useRef(0);
  function handleBidDetailsResizeStart(e: React.MouseEvent<HTMLDivElement, MouseEvent>, colKey: BidDetailsColKey) {
    resizingCol.current = colKey;
    startX.current = e.clientX;
    startWidth.current = bidDetailsColWidths[colKey];
    document.addEventListener('mousemove', handleBidDetailsResizeMove as any);
    document.addEventListener('mouseup', handleBidDetailsResizeEnd as any);
    e.preventDefault();
  }
  function handleBidDetailsResizeMove(e: MouseEvent) {
    if (!resizingCol.current) return;
    const dx = e.clientX - startX.current;
    setBidDetailsColWidths((prev) => ({
      ...prev,
      [resizingCol.current as BidDetailsColKey]: Math.max(60, startWidth.current + dx),
    }));
  }
  function handleBidDetailsResizeEnd() {
    resizingCol.current = null;
    document.removeEventListener('mousemove', handleBidDetailsResizeMove as any);
    document.removeEventListener('mouseup', handleBidDetailsResizeEnd as any);
  }

  // --- Add state for vendor dropdown ---
  const [showVendorDropdown, setShowVendorDropdown] = React.useState(false);

  // Hide number input arrows for all browsers
  // This will be injected into the DOM
  React.useEffect(() => {
    const style = document.createElement('style');
    style.innerHTML = `
      input[type=number].hide-number-arrows::-webkit-inner-spin-button, 
      input[type=number].hide-number-arrows::-webkit-outer-spin-button {
        -webkit-appearance: none;
        margin: 0;
      }
      input[type=number].hide-number-arrows {
        -moz-appearance: textfield;
      }
    `;
    document.head.appendChild(style);
    return () => { document.head.removeChild(style); };
  }, []);

  return (
    <div className="bg-[#ffffff] box-border content-stretch flex flex-col items-start justify-start p-0 relative size-full min-h-screen">
      {/* Header */}
      <ProjectHeader />
      <DndProvider backend={HTML5Backend}>
        {/* Upload Modal as Popup */}
        {showUploadModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="bg-white rounded-xl shadow-xl p-0 w-full max-w-md relative flex flex-col items-center border border-zinc-200">
              <button
                className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-900 text-2xl font-bold"
                onClick={() => setShowUploadModal(false)}
                aria-label="Close"
              >
                &times;
              </button>
              {/* Popup content */}
              <div className="w-full flex flex-col items-center px-8 pt-8 pb-6">
                <div className="mb-4 flex items-center justify-center w-16 h-16 rounded-full bg-zinc-100">
                  {/* Placeholder SVG icon, replace with Figma asset if available */}
                  <svg width="32" height="32" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="text-zinc-900">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 16V4m0 0l-4 4m4-4l4 4M4 20h16" />
                  </svg>
                </div>
                <h2 className="text-xl font-bold text-zinc-900 mb-1 text-center">Upload Bids</h2>
                <p className="text-zinc-500 text-sm mb-6 text-center">Drag and drop your bid file here, or click to browse.</p>
                <form onSubmit={handleUploadSubmit} className="flex flex-col gap-4 w-full items-center">
                  <label htmlFor="file-upload" className="w-full cursor-pointer flex flex-col items-center justify-center border-2 border-dashed border-zinc-900 rounded-xl bg-zinc-100 py-8 px-4 mb-2 transition hover:border-zinc-800">
                    <input
                      id="file-upload"
                      type="file"
                      onChange={handleFileChange}
                      className="hidden"
                      required
                    />
                    <span className="text-zinc-900 font-medium text-sm">{selectedFile ? selectedFile.name : 'Click or drag file to upload'}</span>
                  </label>
                  <div className="flex flex-row gap-2 w-full mt-2">
                    <Button
                      type="button"
                      variant="secondary"
                      className="flex-1"
                      onClick={() => setShowUploadModal(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      variant="default"
                      className="flex-1 bg-zinc-900 hover:bg-zinc-800 text-white"
                      disabled={!selectedFile}
                    >
                      Upload
                    </Button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}
        {/* Update RFP Modal as Popup */}
        {showUpdateRfpModal && (
          <ExactRfpModal
            open={showUpdateRfpModal}
            onClose={() => setShowUpdateRfpModal(false)}
            mode="update"
            projectName={projectName}
            setProjectName={setProjectName}
            file={updateRfpFile}
            setFile={setUpdateRfpFile}
            rfpVersions={rfpVersions}
            currentRfpVersion={0}
            onVersionChange={undefined}
            onSubmit={() => { setShowUpdateRfpModal(false); setUpdateRfpFile(null); }}
            loading={false}
          />
        )}
        {/* Bid Details Modal */}
        {showBidDetails && selectedBid && (
          <Dialog open={showBidDetails} onOpenChange={setShowBidDetails}>
            <DialogContent
              className="bg-background rounded-lg border shadow-lg flex flex-col items-center justify-center"
              style={{ width: '90%', height: 'auto', maxWidth: '1080px', maxHeight: '900px', padding: 0 }}
            >
              <DialogHeader className="px-6 pt-6 w-full flex flex-col items-start">
                <DialogTitle className="text-2xl font-semibold text-left w-full">Bid Details</DialogTitle>
                {/* Vendor Dropdown Switcher - left aligned below the title, Figma spacing and font */}
                <div className="relative mt-4">
                  <button
                    type="button"
                    className="flex items-center gap-[6px] px-[12px] py-[4px] rounded-md border border-zinc-200 bg-white shadow-sm font-[Inter] font-semibold text-[16px] leading-[24px] text-zinc-950 hover:bg-zinc-50 focus:outline-none focus:ring-2 focus:ring-teal-600"
                    style={{ fontWeight: 600, fontFamily: 'Inter, sans-serif', lineHeight: '24px' }}
                    onClick={() => setShowVendorDropdown((v) => !v)}
                  >
                    <span>{selectedBid.vendor}</span>
                    <svg className={`w-4 h-4 transition-transform ${showVendorDropdown ? 'rotate-180' : ''}`} viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M6 6l2 2 2-2" stroke="#09090b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </button>
                  {showVendorDropdown && (
                    <div className="absolute left-0 mt-2 w-48 bg-white border border-zinc-200 rounded-md shadow-lg z-50">
                      {vendorColumnIds.map((vendor) => (
                        <button
                          key={vendor}
                          className={`w-full text-left px-[12px] py-[4px] rounded font-[Inter] text-[16px] leading-[24px] ${vendor === selectedBid.vendor ? 'font-semibold text-teal-600' : 'font-normal text-zinc-950'} hover:bg-zinc-100`}
                          style={{ fontWeight: vendor === selectedBid.vendor ? 600 : 400, fontFamily: 'Inter, sans-serif', lineHeight: '24px' }}
                          onClick={() => {
                            setSelectedBid((prev) => prev ? { ...prev, vendor } : null);
                            setShowVendorDropdown(false);
                          }}
                        >
                          {vendor}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </DialogHeader>
              {/* Refactored: Use flex for main content */}
              <div className="flex flex-row w-full gap-4 px-6  pb-0 items-stretch">
                {/* Summary Card */}
                <div className="flex flex-col gap-2 bg-background border rounded-lg p-4 h-full flex-1 min-w-0">
                  <span className="text-base font-semibold">Summary</span>
                  <span className="text-sm text-muted-foreground h-fit">Acme Corp. offers a turnkey integration between our legacy CRM and their AI-driven quoting engine, delivering real-time data sync, automated quote generation, and full maintenance for 12 months.</span>
                </div>
                {/* Key Criteria Breakdown Card */}
                <div className="flex flex-col gap-2 bg-background border rounded-lg p-4 min-w-0 flex-[2]">
                  <span className="text-base font-semibold">Key criteria breakdown</span>
                  <div className="flex flex-row gap-4 w-full flex-1">
                    {/* Overall Score */}
                    <div className="flex flex-col w-auto min-w-fit items-center justify-center px-4 py-4 rounded-md border bg-zinc-200">
                      <span className="text-sm font-medium mb-1">Overall score</span>
                      <span className="font-bold text-3xl leading-8">87</span>
                      <span className="text-base text-muted-foreground">/100</span>
                    </div>
                    {/* Progress Bars */}
                    <div className="flex flex-col w-full gap-2 items-start justify-center">
                      <div className="flex flex-row gap-2 items-center w-full">
                        <span className="text-xs w-[90px]">Technical fit</span>
                        <div className="bg-muted rounded h-2 flex items-center flex-1"><div className="bg-primary h-2 rounded" style={{ width: '80%' }} /></div>
                      </div>
                      <div className="flex flex-row gap-2 items-center w-full">
                        <span className="text-xs w-[90px]">Cost</span>
                        <div className="bg-muted rounded h-2 flex items-center flex-1"><div className="bg-orange-300 h-2 rounded" style={{ width: '60%' }} /></div>
                      </div>
                      <div className="flex flex-row gap-2 items-center w-full">
                        <span className="text-xs w-[90px]">Timeline</span>
                        <div className="bg-muted rounded h-2 flex items-center flex-1"><div className="bg-red-300 h-2 rounded" style={{ width: '25%' }} /></div>
                      </div>
                      <div className="flex flex-row gap-2 items-center w-full">
                        <span className="text-xs w-[90px]">Support</span>
                        <div className="bg-muted rounded h-2 flex items-center flex-1"><div className="bg-emerald-400 h-2 rounded" style={{ width: '70%' }} /></div>
                      </div>
                      <div className="flex flex-row gap-2 items-center w-full">
                        <span className="text-xs w-[90px]">References</span>
                        <div className="bg-muted rounded h-2 flex items-center flex-1"><div className="bg-violet-600 h-2 rounded" style={{ width: '40%' }} /></div>
                      </div>
                    </div>
                  </div>
                </div>
                {/* Buttons */}
                <div className="flex flex-col gap-3 justify-start items-stretch w-fit ">
                   <Button type="button" variant="outline" className="flex items-center gap-2 w-full">
                     <span className="mr-2"><ViewBidIcon /></span>
                     View bid document
                   </Button>
                   <Button type="button" variant="outline" className="flex items-center gap-2 w-full">
                     <span className="mr-2"><CompareIcon /></span>
                     Compare with another
                   </Button>
                </div>
              </div>
              {/* Tabs */}
              <div className="px-6 pb-6 w-full">
                <Tabs defaultValue="score" className="w-full">
                  <TabsList className="w-full mb-2">
                    <TabsTrigger value="score">Score Details</TabsTrigger>
                    <TabsTrigger value="vendor">Vendor Profile</TabsTrigger>
                    <TabsTrigger value="chat">Chat</TabsTrigger>
                  </TabsList>
                  <TabsContent value="score" className="bg-background rounded-lg border w-full p-0">
                    <div className="overflow-auto max-h-[400px]">
                      <table className="w-full border-collapse">
                        <thead className="sticky top-0 bg-background border-b">
                          <tr>
                            {bidDetailsColOrder.map((col, idx) => (
                              <th
                                key={col.key}
                                className={`relative px-2 py-3 text-xs font-semibold border-r last:border-r-0 ${
                                  col.key === 'score' ? 'text-center' : 'text-left'
                                }`}
                                style={{
                                  width: bidDetailsColWidths[col.key],
                                  minWidth: bidDetailsColWidths[col.key],
                                }}
                              >
                                {col.label}
                                {/* Resize handle, except for justification */}
                                {col.key !== 'justification' && (
                                  <div
                                    onMouseDown={e => handleBidDetailsResizeStart(e, col.key)}
                                    className="absolute right-0 top-0 h-full w-2 cursor-col-resize hover:bg-primary/20 transition-colors"
                                    style={{ zIndex: 2 }}
                                  />
                                )}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {data.map((mainRow) => {
                            const isExpandable = Array.isArray(mainRow.sub) && mainRow.sub.length > 0;
                            const isExpanded = scoreDetailsExpandedRows.includes(mainRow.id);
                            const toggleRow = (id: string) => {
                              setScoreDetailsExpandedRows(prev => 
                                prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
                              );
                            };
                            
                            return (
                              <React.Fragment key={mainRow.id}>
                                <tr
                                  className={`border-b hover:bg-muted/50 transition-colors ${
                                    isExpandable ? 'cursor-pointer' : ''
                                  }`}
                                  onClick={() => isExpandable && toggleRow(mainRow.id)}
                                >
                                  <td 
                                    className="px-2 py-2 font-normal text-sm border-r"
                                    style={{ width: bidDetailsColWidths.criteria }}
                                  >
                                    <div className="flex items-center">
                                      {isExpandable ? (
                                        <button
                                          className={`mr-2 p-1 hover:bg-muted rounded transition-transform flex-shrink-0 ${
                                            isExpanded ? 'rotate-90' : ''
                                          }`}
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            toggleRow(mainRow.id);
                                          }}
                                        >
                                          <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                                            <path 
                                              d="M6 4l4 4-4 4" 
                                              stroke="currentColor" 
                                              strokeWidth="2" 
                                              strokeLinecap="round" 
                                              strokeLinejoin="round"
                                            />
                                          </svg>
                                        </button>
                                      ) : (
                                        <span className="w-6 mr-2 flex-shrink-0" />
                                      )}
                                      <span className="font-medium">{mainRow.title}</span>
                                    </div>
                                  </td>
                                  <td 
                                    className="px-2 py-2 text-center text-sm border-r"
                                    style={{ width: bidDetailsColWidths.score }}
                                  >
                                    {mainRow.weight}
                                  </td>
                                  <td 
                                    className="px-2 py-2 text-sm border-r"
                                    style={{ width: bidDetailsColWidths.justification }}
                                  >
                                    Main criteria justification goes here.
                                  </td>
                                  <td 
                                    className="px-2 py-2 text-sm"
                                    style={{ width: bidDetailsColWidths.reference }}
                                  >
                                    <div className="flex items-center">
                                      <span className="mr-2">
                                        <ReferenceIcon />
                                      </span>
                                      <span className="text-xs text-muted-foreground">Section</span>
                                    </div>
                                  </td>
                                </tr>
                                {/* Sub-criteria rows */}
                                {isExpanded && mainRow.sub && mainRow.sub.map(sub => (
                                  <tr key={sub.id} className="border-b bg-muted/20 hover:bg-muted/40 transition-colors">
                                    <td 
                                      className="px-2 py-2 text-sm border-r"
                                      style={{ width: bidDetailsColWidths.criteria }}
                                    >
                                      <div className="flex items-center">
                                        <span className="w-6 mr-2 flex-shrink-0" />
                                        <span className="w-4 mr-2 flex-shrink-0" />
                                        <span>{sub.text}</span>
                                      </div>
                                    </td>
                                    <td 
                                      className="px-2 py-2 text-center text-sm border-r"
                                      style={{ width: bidDetailsColWidths.score }}
                                    >
                                      {(() => {
                                        // Find vendor index
                                        const vendorIdx = ['LangeTech', 'Best Pacific', 'KMNM', 'Bhilosa', 'Tianhai Lace'].indexOf(selectedBid.vendor);
                                        if (vendorIdx !== -1 && sub.scores && sub.scores[vendorIdx]) {
                                          return sub.scores[vendorIdx];
                                        }
                                        return '-';
                                      })()}
                                    </td>
                                    <td 
                                      className="px-2 py-2 text-sm border-r"
                                      style={{ width: bidDetailsColWidths.justification }}
                                    >
                                      Sub-criteria justification goes here.
                                    </td>
                                    <td 
                                      className="px-2 py-2 text-sm"
                                      style={{ width: bidDetailsColWidths.reference }}
                                    >
                                      <div className="flex items-center">
                                        <span className="mr-2">
                                          <ReferenceIcon />
                                        </span>
                                        <span className="text-xs text-muted-foreground">Sub</span>
                                      </div>
                                    </td>
                                  </tr>
                                ))}
                              </React.Fragment>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </TabsContent>
                  <TabsContent value="vendor" className="bg-background rounded-b-lg shadow w-full px-0 pb-0 pt-4">
                    <div className="flex flex-col gap-6 w-full px-6 pb-6">
                      {/* Top: Company Info */}
                      <div className="flex flex-row gap-8 items-center">
                        <div className="flex flex-col gap-1">
                          <span className="text-2xl font-bold text-zinc-950">Acme Corp.</span>
                          <span className="text-sm text-zinc-500">HQ: Casablanca, Morocco</span>
                          <span className="text-sm text-zinc-500">Employees: 120</span>
                          <span className="text-sm text-zinc-500">Annual Revenue: $15 M</span>
                        </div>
                      </div>
                      {/* Executive Summary */}
                      <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4 flex flex-col gap-2">
                        <span className="text-base font-semibold text-zinc-950 mb-1">Executive Summary</span>
                        <span className="text-sm text-zinc-700">Acme Corp. offers a turnkey integration between our legacy CRM and their AI-driven quoting engine, delivering real-time data sync, automated quote generation, and full maintenance for 12 months.</span>
                      </div>
                      {/* Highlights & Risks side by side */}
                      <div className="flex flex-col md:flex-row gap-6 w-full">
                        {/* Highlights */}
                        <div className="bg-emerald-50 border border-emerald-100 rounded-lg p-4 flex-1 flex flex-col gap-2 min-w-0">
                          <span className="text-base font-semibold text-emerald-900 mb-1">Highlights</span>
                          <ul className="list-disc pl-5 text-sm text-emerald-900">
                            <li>Custom API connectors for all major data endpoints</li>
                            <li>Delivery milestone 2 weeks ahead of schedule</li>
                            <li>12 months free maintenance &amp; patch updates</li>
                          </ul>
                        </div>
                        {/* Risks & Concerns */}
                        <div className="bg-orange-50 border border-orange-100 rounded-lg p-4 flex-1 flex flex-col gap-2 min-w-0">
                          <span className="text-base font-semibold text-orange-900 mb-1">Risks &amp; Concerns</span>
                          <ul className="list-disc pl-5 text-sm text-orange-900">
                            <li>Travel costs not covered in the base fee</li>
                            <li>No local office for in-person support</li>
                          </ul>
                        </div>
                      </div>
                    </div>
                  </TabsContent>
                  <TabsContent value="chat" className="bg-background rounded-b-lg shadow w-full px-0 pb-0 pt-4">
                    <ChatTabContent />
                  </TabsContent>
                </Tabs>
              </div>
            </DialogContent>
          </Dialog>
        )}
        <div
          className="bg-[#ffffff] box-border content-stretch flex flex-col items-start justify-start p-0 relative size-full"
          data-name="Project"
          id="node-1_150"
        >
          
          
          
          {/* Main Content and Table */}
          <div className="bg-[#ffffff] relative rounded-lg shrink-0 w-full max-w-[1400px] mx-auto" data-name="Wrapper" id="node-1_161">
            <div className="flex flex-col items-center relative size-full">
              <div className="box-border content-stretch flex flex-col gap-8 items-center justify-start p-[32px] relative w-full">
                {/* Title and Actions */}
                <div className="box-border content-stretch flex flex-row items-center justify-between p-0 relative shrink-0 w-full" data-name="Wrapper" id="node-1_162">
                  <div className="box-border content-stretch flex flex-col gap-1.5 items-start justify-center p-0 relative shrink-0" id="node-1_163">
                    <div className="box-border content-stretch flex flex-row gap-2.5 items-center justify-center p-0 relative shrink-0" data-name="Title" id="node-1_164">
                      <div className="font-['Inter:Semi_Bold',_sans-serif] font-semibold leading-[0] not-italic relative shrink-0 text-[#000000] text-[24px] text-left text-nowrap" id="node-1_165">
                        <p className="block leading-[32px] whitespace-pre">ERP System Implimentation</p>
                      </div>
                    </div>
                    <div className="box-border content-stretch flex flex-row gap-2.5 items-center justify-center p-0 relative shrink-0" data-name="Text" id="node-1_166">
                      <div className="font-['Inter:Regular',_sans-serif] font-normal leading-[0] not-italic relative shrink-0 text-[#000000] text-[16px] text-left text-nowrap" id="node-1_167">
                        <p className="block leading-[24px] whitespace-pre">Looking for a comprehensive ERP solution for our manufacturing operations</p>
                      </div>
                    </div>
                  </div>
                  <div className="box-border content-stretch flex flex-col gap-4 items-end justify-start p-0 relative shrink-0" id="node-1_168">
                    <button type="button" className="bg-white hover:bg-zinc-100 box-border content-stretch flex flex-row gap-1.5 h-8 items-center justify-start px-2.5 py-0 relative rounded-md shrink-0 transition-colors focus:outline-none" data-name="Filter" id="node-1_169"
                      onClick={() => setShowUpdateRfpModal(true)}
                    >
                      <div className="absolute border border-solid border-zinc-200 inset-0 pointer-events-none rounded-md shadow-[0px_1px_2px_0px_rgba(0,0,0,0.1)]" />
                      <div className="overflow-clip relative shrink-0 size-4" data-name="upload" id="node-1_170">
                        <div className="absolute inset-[12.5%]" data-name="Vector" id="node-I1_170-128_2807">
                          <div className="absolute inset-[-4.167%]">
                            <img alt="Upload Icon" className="block max-w-none size-full" src={img3} />
                          </div>
                        </div>
                      </div>
                      <div className="box-border content-stretch flex flex-row gap-2.5 items-center justify-center p-0 relative shrink-0" data-name="Text" id="node-1_171">
                        <div className="font-['Inter:Medium',_sans-serif] font-medium leading-[0] not-italic relative shrink-0 text-[12px] text-left text-nowrap text-zinc-950" id="node-1_172">
                          <p className="block leading-[16px] whitespace-pre">Update RFP</p>
                        </div>
                      </div>
                    </button>
                    <button type="button" className="bg-white hover:bg-zinc-100 box-border content-stretch flex flex-row gap-1.5 h-8 items-center justify-start px-2.5 py-0 relative rounded-md shrink-0 transition-colors focus:outline-none" data-name="Filter" id="node-1_173"
                      onClick={() => setShowBlade(true)}
                    >
                      <div className="absolute border border-solid border-teal-600 inset-0 pointer-events-none rounded-md shadow-[0px_1px_2px_0px_rgba(0,0,0,0.1)]" />
                      <div className="relative shrink-0 size-4" data-name="Frame" id="node-1_174">
                        <img alt="Frame Icon" className="block max-w-none size-full" src={imgFrame} />
                      </div>
                      <div className="box-border content-stretch flex flex-row gap-2.5 items-center justify-center p-0 relative shrink-0" data-name="Text" id="node-1_176">
                        <div className="font-['Inter:Medium',_sans-serif] font-medium leading-[0] not-italic relative shrink-0 text-[12px] text-left text-nowrap text-zinc-950" id="node-1_177">
                          <p className="block leading-[16px] whitespace-pre">Ask anything</p>
                        </div>
                      </div>
                    </button>
                  </div>
                </div>
                {/* Table and Filters */}
                <div className="box-border content-stretch flex flex-col gap-4 items-start justify-start p-0 relative shrink-0 w-full" data-name="Wrapper" id="node-1_178">
                  {/* Total Weight Display */}
                  {/* <div className="mb-2 text-sm font-medium text-zinc-700">Total Weight: {totalWeight}%</div> */}
                    {/* Search, Filter, View, Add Bids Row */}
                  <div className="flex flex-row items-center justify-end w-full gap-x-2 ">
                    <Input
                      className="w-full max-w-xs"
                      placeholder="Search table..."
                      value={searchTerm}
                      onChange={e => setSearchTerm(e.target.value)}
                      type="text"
                    />
                    <DataTableFilter
                      columns={filterColumns}
                      filters={filters}
                      actions={actions}
                      strategy={strategy}
                      disabled={true}
                    />
                      <button type="button" className="bg-white hover:bg-zinc-100 box-border content-stretch flex flex-row gap-1.5 h-8 items-center justify-start px-2.5 py-0 relative rounded-md shrink-0 w-[77px] transition-colors focus:outline-none" data-name="Filter" id="node-1_197">
                        <div className="absolute border border-solid border-zinc-200 inset-0 pointer-events-none rounded-md shadow-[0px_1px_2px_0px_rgba(0,0,0,0.1)]" />
                        <div className="overflow-clip relative shrink-0 size-4" data-name="settings-2" id="node-1_198">
                          <div className="absolute inset-[16.667%]" data-name="Vector" id="node-I1_198-128_2305">
                            <div className="absolute inset-[-4.688%]">
                              <img alt="Settings" className="block max-w-none size-full" src={img6} />
                            </div>
                          </div>
                        </div>
                        <div className="box-border content-stretch flex flex-row gap-2.5 items-center justify-center p-0 relative shrink-0" data-name="Text" id="node-1_199">
                          <div className="font-['Inter:Medium',_sans-serif] font-medium leading-[0] not-italic relative shrink-0 text-[12px] text-left text-nowrap text-zinc-950" id="node-1_200">
                            <p className="block leading-[16px] whitespace-pre">View</p>
                          </div>
                        </div>
                      </button>
                      <button type="button" className="bg-zinc-950 hover:bg-zinc-800 box-border content-stretch flex flex-row gap-1.5 h-full items-center justify-center px-5 py-2 relative rounded-md shadow-[0px_1px_2px_0px_rgba(0,0,0,0.1)] shrink-0 transition-colors focus:outline-none" data-name="Filter" id="node-1_201"
                        onClick={() => setShowUploadModal(true)}
                      >
                        <div className="overflow-clip relative shrink-0 size-4" data-name="upload" id="node-1_202">
                          <div className="absolute inset-[12.5%]" data-name="Vector" id="node-I1_202-128_2807">
                            <div className="absolute inset-[-4.167%]">
                              <img alt="Upload" className="block max-w-none size-full" src={img7} />
                            </div>
                          </div>
                        </div>
                        <div className="box-border content-stretch flex flex-row gap-2.5 items-center justify-center p-0 relative shrink-0" data-name="Text" id="node-1_203">
                          <div className="font-['Inter:Medium',_sans-serif] font-medium leading-[0] not-italic relative shrink-0 text-[12px] text-left text-neutral-50 text-nowrap" id="node-1_204">
                            <p className="block leading-[16px] whitespace-pre">Add Bids</p>
                            </div>
                          </div>
                        </button>
                      </div>
                    </div>
                  {/* Table Structure (headers and sample row) */}
                  <div className="bg-[#ffffff]  relative rounded-md shrink-0 w-full" data-name="Table" id="node-1_205">
                    <div className="box-border rounded-md border-zinc-200 border-2 content-stretch flex flex-col items-start justify-start overflow-clip p-0 relative w-full">
                      <table className="min-w-full border-collapse rounded-lg">
                        <thead className="bg-zinc-100 font-semibold text-zinc-950 border-b border-zinc-200 sticky top-[56px] z-20">
                          {table.getHeaderGroups().map(headerGroup => (
                            <tr key={headerGroup.id}>
                              {headerGroup.headers.map((header, i) => (
                                <DraggableTh key={header.id} header={header} index={i} moveColumn={moveColumn} />
                              ))}
                            </tr>
                          ))}
                        </thead>
                        <tbody>
                          {table.getRowModel().rows.map(row => row.depth < 1 && (
                            <React.Fragment key={row.id}>
                              <tr
                                className="bg-zinc-100 border-b border-zinc-200 cursor-pointer transition-colors hover:bg-zinc-100 focus-within:bg-zinc-100 outline-none"
                                style={{ background: '#fff' }}
                                tabIndex={0}
                                onClick={() => row.toggleExpanded()}
                              >
                                {row.getVisibleCells().map(cell => (
                                  <td key={cell.id} className={`px-2 py-2 font-normal text-sm leading-5 text-zinc-950 text-left ${cell.getContext().cell.column.getIndex() > 0 ? 'border-l border-zinc-200' : ''}`}>
                                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                  </td>
                                ))}
                              </tr>
                              {row.getIsExpanded() && row.subRows.length > 0 && row.subRows.map(subRow => (
                                <tr
                                  key={subRow.id}
                                  className="bg-white border-b border-zinc-100 transition-colors hover:bg-zinc-50 focus-within:bg-zinc-50 outline-none"
                                  style={{ background: '#fff' }}
                                  tabIndex={0}
                                >
                                  {subRow.getVisibleCells().map((cell, i) => (
                                    <td
                                      key={cell.id}
                                      className={`py-2 font-normal text-sm leading-5 text-zinc-950 text-left ${i === 0 ? 'pl-8' : 'px-2'} ${cell.getContext().cell.column.getIndex() > 0 ? 'border-l border-zinc-200' : ''}`}
                                    >
                                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </React.Fragment>
                          ))}
                        </tbody>
                        <tfoot>
                          <tr className="sticky bottom-0 bg-zinc-200 text-zinc-900 font-bold shadow-lg rounded-b-md">
                            {columnOrder.map((colId, idx) => {
                              if (colId === 'title') {
                                return <td key={colId} className="px-2 py-2 text-left">Overall Score</td>;
                              }
                              if (colId === 'weight') {
                                return <td key={colId} className="px-2 py-2 border-l border-zinc-200" />;
                              }
                              // Vendor columns
                              const vendorIdx = vendorColumnIds.indexOf(colId);
                              // For each main section (5.1 to 5.6), get the vendor's score and weight from data
                              const sectionIds = ['5.1', '5.2', '5.3', '5.4', '5.5', '5.6'];
                              const sectionScores = sectionIds.map((sectionId) => {
                                const sectionRow = data.find(row => row.id === sectionId);
                                if (!sectionRow) return 0;
                                const scoreStr = sectionRow.scores[vendorIdx];
                                return Number(scoreStr.replace('%','')) || 0;
                              });
                              const sectionWeights = sectionIds.map((sectionId) => {
                                const sectionRow = data.find(row => row.id === sectionId);
                                if (!sectionRow) return 0;
                                return Number(sectionRow.weight.replace('%','')) || 0;
                              });
                              return <td key={colId} className="px-2 py-2 text-left border-l border-zinc-200">{calculateOverallScore(sectionScores, sectionWeights)}%</td>;
                            })}
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                    <div className="absolute border border-solid border-zinc-200 inset-0 pointer-events-none rounded-md" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </DndProvider>
        {/* Blade for Ask Anything chat */}
        {showBlade && (
          <div className="fixed inset-0 z-50 flex">
            {/* Overlay */}
            <div className="absolute inset-0 bg-black/30 transition-opacity" onClick={() => setShowBlade(false)} />
            {/* Blade panel */}
            <div className="relative ml-auto h-full w-full max-w-md bg-background shadow-xl border-l border-zinc-200 flex flex-col animate-slide-in-right">
              <div className="flex items-center justify-between px-6 py-4 border-b">
                <span className="text-lg font-semibold">Ask Anything</span>
                <button className="text-2xl font-bold text-zinc-400 hover:text-zinc-900" onClick={() => setShowBlade(false)} aria-label="Close">&times;</button>
              </div>
              <div className="flex-1 overflow-y-auto">
                <ChatTabContent />
              </div>
            </div>
            <style>{`
              @keyframes slide-in-right {
                from { transform: translateX(100%); }
                to { transform: translateX(0); }
              }
              .animate-slide-in-right {
                animation: slide-in-right 0.3s cubic-bezier(0.4,0,0.2,1);
              }
            `}</style>
          </div>
        )}
      </div>
    );
} 

// --- ChatTabContent component ---
function ChatTabContent() {
  const { messages, input, handleInputChange, handleSubmit, status, error, stop, reload } = useChat({});
  return (
    <div className="flex flex-col h-[400px] max-h-[400px] w-full px-4">
      <div className="flex-1 overflow-y-auto mb-2 border rounded bg-white p-2">
        {messages.length === 0 && (
          <div className="text-muted-foreground text-center py-8">Start a conversation about this bid…</div>
        )}
        {messages.map((m: any) => (
          <div key={m.id} className={`mb-2 flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`rounded px-3 py-2 max-w-[80%] text-sm ${m.role === 'user' ? 'bg-zinc-200 text-right' : 'bg-zinc-100 text-left'}`}>
              <span className="block font-semibold mb-1 text-xs text-zinc-500">{m.role === 'user' ? 'You' : 'AI'}</span>
              {m.content}
            </div>
          </div>
        ))}
        {status === 'streaming' && (
          <div className="mb-2 flex justify-start">
            <div className="rounded px-3 py-2 bg-zinc-100 text-left text-sm animate-pulse">AI is typing…</div>
          </div>
        )}
      </div>
      {error && (
        <div className="text-red-500 text-xs mb-2 flex items-center gap-2">
          <span>Something went wrong.</span>
          <button className="underline" onClick={() => reload()}>Retry</button>
        </div>
      )}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-600"
          name="prompt"
          value={input}
          onChange={handleInputChange}
          placeholder="Type your message…"
          disabled={status === 'streaming'}
        />
        <button
          type="submit"
          className="bg-zinc-900 text-white px-4 py-2 rounded disabled:opacity-50"
          disabled={status === 'streaming' || !input.trim()}
        >
          Send
        </button>
        {(status === 'streaming' || status === 'submitted') && (
          <button type="button" className="ml-2 text-xs underline" onClick={stop}>Stop</button>
        )}
      </form>
    </div>
  );
}

// 1. Add a Tooltip component at the top of the file (after imports):

function Tooltip({ children, text }: { children: React.ReactNode; text: string }) {
  const [visible, setVisible] = React.useState(false);
  return (
    <span style={{ position: 'relative', display: 'inline-block' }}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {visible && (
        <span style={{
          position: 'absolute',
          bottom: '120%',
          left: '50%',
          transform: 'translateX(-50%)',
          background: '#222',
          color: '#fff',
          padding: '6px 12px',
          borderRadius: '4px',
          fontSize: '12px',
          whiteSpace: 'pre-line',
          zIndex: 1000,
          pointerEvents: 'none',
          minWidth: '120px',
          maxWidth: '240px',
        }}>{text}</span>
      )}
    </span>
  );
}

import ExactRfpModal from "../components/ExactRfpModal";