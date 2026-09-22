const hasPrice = (value) => value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));

export function offersFor(quote) {
  const base = { quote, goods: quote.market.goods_total };
  return [
    { ...base, freight: null, key: "q" + quote.id, shipping: quote.market.shipping_total, issues: quote.market.issues },
    ...(quote.freight_offers || []).filter((f) => f.is_live).map((f) => ({ ...base, freight: f, key: "f" + f.id, shipping: f.total_cost, issues: f.issues })),
  ].map((o) => ({ ...o,
    total: hasPrice(o.goods) && hasPrice(o.shipping) ? Number(o.goods) + Number(o.shipping) : null,
    group: quote.market.comparison_key ? quote.market.comparison_key + "|" + (quote.available_at || "") + "|" + (o.freight ? o.freight.terms + "|" + o.freight.delivery_days : quote.delivery_terms) : null,
  }));
}

export function isBestOffer(offer, offers) {
  if (!offer.group || offer.total === null || offer.issues.length) return false;
  const peers = offers.filter((o) => o.group === offer.group && !o.issues.length && o.total !== null);
  return peers.length > 1 && peers.every((o) => o.total >= offer.total);
}
