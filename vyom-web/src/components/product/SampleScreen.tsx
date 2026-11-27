import type { ProductSlug } from '@/content/products';
import { literatureStages } from '@/content/products';
import {
  CaseDetailPane,
  CaseQueue,
  FlaggedArticles,
  LiteratureFunnel,
  ReportOutline,
  VendorScorecard,
} from '@/components/mocks';

/**
 * The sample screen for each module. Every one of these carries a
 * SAMPLE DATA chip and uses fictional identifiers only.
 */
export function SampleScreen({ slug }: { readonly slug: ProductSlug }) {
  switch (slug) {
    case 'radar':
      return (
        <div className="flex flex-col gap-4">
          <div className="rounded-panel border border-strong bg-panel p-[22px] shadow-panel">
            <LiteratureFunnel data={literatureStages} />
          </div>
          <FlaggedArticles />
        </div>
      );

    case 'verify':
      return (
        <div className="flex flex-col gap-4">
          <CaseQueue />
          <CaseDetailPane />
          <VendorScorecard trend />
        </div>
      );

    case 'dossier':
      return <ReportOutline />;
  }
}
