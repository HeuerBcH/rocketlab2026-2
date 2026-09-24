import type { components, operations } from './schema'

type Schemas = components['schemas']

export type MovieListItem = Schemas['MovieListItem']
export type MovieDetail = Schemas['MovieDetail']
export type MoviePage = Schemas['Page_MovieListItem_']
export type MovieCreate = Schemas['MovieCreate']
export type MovieUpdate = Schemas['MovieUpdate']
export type MovieSort = Schemas['MovieSort']
export type MovieStatus = Schemas['MovieStatus']
export type RatingSummary = Schemas['RatingSummary']
export type Genre = Schemas['GenreOut']
export type Person = Schemas['PersonOut']
export type Review = Schemas['ReviewOut']
export type ReviewPage = Schemas['Page_ReviewOut_']
export type ReviewCreate = Schemas['ReviewCreate']
export type ReviewCreated = Schemas['ReviewCreated']

/** Parâmetros aceitos pelo catálogo (GET /movies). */
export type MovieListParams = NonNullable<
  operations['list_movies_api_v1_movies_get']['parameters']['query']
>
