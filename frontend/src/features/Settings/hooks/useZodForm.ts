/**
 * useZodForm
 * Reusable hook to integrate Zod schemas with React Hook Form (RHF)
 */
import { useMemo } from 'react';
import {
  useForm,
  type DefaultValues,
  type Mode,
  type UseFormReturn,
  type FieldValues,
  type Resolver,
} from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import type { z } from 'zod';

type ZodSchemaFor = z.ZodTypeAny;

export interface UseZodFormParams<TFieldValues extends FieldValues> {
  schema: ZodSchemaFor;
  defaultValues?: DefaultValues<TFieldValues>;
  mode?: Mode;
}

export function useZodForm<TFieldValues extends FieldValues>(
  params: UseZodFormParams<TFieldValues>,
): UseFormReturn<TFieldValues> {
  const { schema, defaultValues, mode = 'onChange' } = params;

  const resolver = useMemo<Resolver<TFieldValues>>(
    () => zodResolver(schema as never) as Resolver<TFieldValues>,
    [schema],
  );

  return useForm<TFieldValues>({
    resolver,
    defaultValues,
    mode,
    criteriaMode: 'all',
    progressive: true,
  });
}

export function zodResolverFor<TFieldValues extends FieldValues>(
  schema: ZodSchemaFor,
): Resolver<TFieldValues> {
  return zodResolver(schema as never) as Resolver<TFieldValues>;
}

/**
 * Voorbeeldgebruik:
 *
 * const form = useZodForm({ schema: orgProfileSchema, defaultValues: { name: '' } });
 * return (
 *   <FormProvider {...form}>
 *     <form onSubmit={form.handleSubmit(onSubmit)}>
 *       ...
 *     </form>
 *   </FormProvider>
 * );
 */
