import { AppProps } from 'next/app';
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Layout } from "@/components/Layout";
import { useRouter } from 'next/router';
import Head from 'next/head';
import '../index.css';

const queryClient = new QueryClient();

export default function MyApp({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const isNotFound = router.pathname === '/404';

  return (
    <QueryClientProvider client={queryClient}>
      <Head>
        <title>Ultron</title>
        <link rel="icon" href="/favicon.png" />
      </Head>
      <TooltipProvider>

        <Toaster />
        <Sonner />
        {isNotFound ? (
          <Component {...pageProps} />
        ) : (
          <Layout>
            <Component {...pageProps} />
          </Layout>
        )}
      </TooltipProvider>
    </QueryClientProvider>
  );
}
