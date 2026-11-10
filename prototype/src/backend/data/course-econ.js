import { q, fc, sub } from './helpers.js'

export const courseEcon = {
  id: 'econ-101',
  code: 'ECON 101',
  title: 'Principles of Microeconomics',
  department: 'Economics',
  credits: 3,
  level: 'Undergraduate · Year 1',
  accent: '#4d6b2f',
  description:
    'How individuals and firms make decisions, and how markets coordinate them. Demand, supply, elasticity and market structures.',
  instructorId: 'u-lee',
  status: 'published',
  source: { fileName: 'ECON101-outline.docx' },
  topics: [
    {
      id: 'econ-t1',
      title: 'Supply and Demand',
      subtopics: [
        sub('econ-dem', 'Demand', 'The law of demand, the demand curve and what shifts it.', {
          points: ['Law of demand: higher price, lower quantity demanded', 'A price change moves along the curve', 'Income, tastes and related goods shift the curve', 'Normal goods rise with income; inferior goods fall'],
          summary: [
            'The law of demand says that, other things equal, a higher price reduces the quantity demanded. This is shown as a downward-sloping demand curve. A change in the good’s own price causes a movement along the curve.',
            'A change in anything else (consumer income, tastes, the price of substitutes or complements, expectations, the number of buyers) shifts the whole curve. For a normal good, higher income raises demand; for an inferior good, higher income lowers it.',
          ],
          cards: [fc('What is the law of demand?', 'Other things equal, a higher price leads to a lower quantity demanded.'), fc('What causes movement along a demand curve?', 'A change in the good’s own price.'), fc('What is an inferior good?', 'A good whose demand falls when consumer income rises.')],
          questions: [
            q('A rise in the price of a good causes which change on its demand curve?', 'A movement along the curve to a lower quantity', ['A rightward shift', 'A leftward shift', 'No change'], 'Own-price changes move along the curve; they do not shift it.'),
            q('Which of the following shifts the demand curve for coffee to the right?', 'A rise in the price of tea, a substitute', ['A rise in the price of coffee', 'A fall in the price of coffee', 'A rise in the cost of coffee beans'], 'A pricier substitute pushes buyers toward coffee at every price.'),
            q('What happens to demand for an inferior good when income rises?', 'It falls', ['It rises', 'It is unchanged', 'It becomes perfectly elastic'], 'By definition, inferior goods lose demand as income grows.'),
            q('What is held constant when drawing a demand curve?', 'Everything except the good’s own price', ['The quantity supplied', 'Consumer income only', 'Nothing'], 'This is the ceteris paribus assumption.'),
          ],
          remediation: {
            explanation: 'Two different questions: "What if the price changes?" (slide along the same curve) versus "What if something else changes?" (the whole curve moves). Ask which one the question is about before you draw anything.',
            steps: ['Draw a demand curve and mark a movement caused by a price fall.', 'Shift the curve for a rise in income of a normal good.', 'Name one inferior good and explain why demand for it falls as incomes rise.'],
          },
        }),
        sub('econ-sup', 'Supply', 'The law of supply, the supply curve and what shifts it.', {
          points: ['Law of supply: higher price, higher quantity supplied', 'Input costs, technology and taxes shift supply', 'A price change moves along the curve', 'The number of sellers affects market supply'],
          summary: [
            'The law of supply says that a higher price increases the quantity producers are willing to supply, giving an upward-sloping supply curve. Again, a change in the good’s own price moves along the curve.',
            'Supply shifts when production conditions change: input prices, technology, taxes and subsidies, expectations and the number of sellers. Better technology or cheaper inputs shift supply right; higher costs shift it left.',
          ],
          cards: [fc('What is the law of supply?', 'A higher price leads to a higher quantity supplied.'), fc('Cheaper inputs do what to supply?', 'Shift the supply curve to the right (increase supply).'), fc('Name two supply shifters.', 'Input prices and technology (also taxes, subsidies, number of sellers).')],
          questions: [
            q('Which event shifts the supply curve of bread to the left?', 'A rise in the price of flour', ['A rise in the price of bread', 'Improved baking technology', 'A fall in the price of flour'], 'Higher input costs reduce supply at every price.'),
            q('A higher market price leads to what for quantity supplied?', 'It rises, a movement along the supply curve', ['It falls', 'The supply curve shifts left', 'It stays fixed'], 'The law of supply is a movement along the curve.'),
            q('What does a per-unit tax on producers do to supply?', 'Shifts it to the left', ['Shifts it to the right', 'Has no effect', 'Makes it perfectly elastic'], 'The tax raises per-unit cost, so less is supplied at each price.'),
            q('What happens to market supply when more firms enter the market?', 'It increases', ['It decreases', 'It is unchanged', 'It becomes vertical'], 'More sellers means more quantity at each price.'),
          ],
          remediation: {
            explanation: 'Supply is about the seller’s side: costs and capabilities. If it gets cheaper or easier to produce, sellers offer more at every price (shift right). If it gets pricier, they offer less (shift left).',
            steps: ['Sketch a supply curve and shift it for improved technology.', 'List three things that would shift supply of wheat.', 'Distinguish "quantity supplied" from "supply" in one sentence.'],
          },
        }),
        sub('econ-eq', 'Market equilibrium', 'How price and quantity are determined where supply meets demand.', {
          points: ['Equilibrium is where quantity demanded equals quantity supplied', 'Above equilibrium there is a surplus; below it a shortage', 'Prices adjust to eliminate surpluses and shortages', 'Shifts in supply or demand create a new equilibrium'],
          summary: [
            'Market equilibrium is the price at which quantity demanded equals quantity supplied. At a price above equilibrium there is a surplus and sellers cut prices; below equilibrium there is a shortage and prices are bid up. The price adjusts until the market clears.',
            'When demand or supply shifts, the equilibrium moves. A rightward demand shift raises both price and quantity. A leftward supply shift raises the price and lowers the quantity.',
          ],
          cards: [fc('What is a surplus?', 'Quantity supplied exceeds quantity demanded, at a price above equilibrium.'), fc('Demand shifts right: effect on equilibrium?', 'Both price and quantity rise.'), fc('Supply shifts left: effect on equilibrium?', 'Price rises and quantity falls.')],
          questions: [
            q('At a price above equilibrium, the market has:', 'A surplus', ['A shortage', 'Exact balance', 'Zero demand'], 'Sellers want to sell more than buyers want to buy, which pushes the price down.'),
            q('Demand increases while supply is unchanged. What happens to the equilibrium?', 'Price and quantity both rise', ['Price rises, quantity falls', 'Price falls, quantity rises', 'Both fall'], 'The new intersection lies up and to the right.'),
            q('Supply decreases while demand is unchanged. What happens to the equilibrium?', 'Price rises and quantity falls', ['Price and quantity both rise', 'Price falls and quantity rises', 'Nothing'], 'The new intersection lies up and to the left.'),
            q('What drives the market toward equilibrium?', 'Price adjustments in response to surpluses and shortages', ['Government orders', 'Fixed quotas', 'Advertising'], 'Competitive pressure moves the price toward the clearing level.'),
          ],
          remediation: {
            explanation: 'Think of an auction. If too many people want the item, the bid rises; if nobody bids, the price drops. The equilibrium is where the bidding settles because buyers and sellers agree.',
            steps: ['Draw supply and demand, mark equilibrium, then mark a price above and below it.', 'Shift demand right and trace the new equilibrium.', 'Do the same for a supply shift left and compare the results.'],
          },
        }),
      ],
    },
    {
      id: 'econ-t2',
      title: 'Elasticity and Welfare',
      subtopics: [
        sub('econ-ela', 'Price elasticity of demand', 'Measuring responsiveness, and the link between elasticity and revenue.', {
          points: ['Elasticity = % change in quantity ÷ % change in price', 'Elastic when the magnitude is greater than 1', 'Substitutes and time make demand more elastic', 'Raising price lowers revenue when demand is elastic'],
          summary: [
            'Price elasticity of demand measures how strongly quantity demanded responds to a price change: the percentage change in quantity divided by the percentage change in price. If the magnitude is greater than one, demand is elastic; below one, inelastic.',
            'Demand tends to be more elastic when close substitutes exist, when the good is a luxury, and over longer time horizons. If demand is elastic, a price rise cuts total revenue; if inelastic, a price rise increases it.',
          ],
          cards: [fc('Formula for price elasticity of demand?', '% change in quantity demanded ÷ % change in price.'), fc('Elastic demand means?', 'Magnitude of elasticity is greater than 1; quantity responds strongly to price.'), fc('Price rises and demand is inelastic: revenue?', 'Revenue rises.')],
          questions: [
            q('Price rises 10% and quantity demanded falls 20%. The elasticity magnitude is:', '2', ['0.5', '10', '30'], '20% ÷ 10% = 2, so demand is elastic.'),
            q('Which factor makes demand more elastic?', 'Availability of close substitutes', ['Being a necessity', 'A short time period', 'Having no alternatives'], 'Substitutes let consumers switch easily when the price rises.'),
            q('If demand is elastic and a firm raises its price, total revenue will:', 'Fall', ['Rise', 'Stay the same', 'Double'], 'The percentage fall in quantity outweighs the percentage rise in price.'),
            q('Demand with elasticity of 0.4 is called:', 'Inelastic', ['Elastic', 'Unit elastic', 'Perfectly elastic'], 'Magnitudes below one are inelastic.'),
          ],
          remediation: {
            explanation: 'Elasticity asks "how much do customers care about the price?". Insulin buyers barely react to a price rise (inelastic). Shoppers choosing between two brands of juice react a lot (elastic).',
            steps: ['Compute elasticity for: price +5%, quantity −15%.', 'Classify milk, a luxury watch and petrol as elastic or inelastic and justify each.', 'Explain what happens to revenue in each case when price rises.'],
          },
        }),
        sub('econ-surplus', 'Consumer and producer surplus', 'Welfare measures for buyers and sellers, and why taxes create deadweight loss.', {
          points: ['Consumer surplus = willingness to pay minus price paid', 'Producer surplus = price received minus cost', 'Total surplus is maximised at equilibrium', 'A tax shrinks trade and creates deadweight loss'],
          summary: [
            'Consumer surplus is the difference between what buyers are willing to pay and what they actually pay; producer surplus is the difference between the price sellers receive and their cost. At competitive equilibrium the sum of both (total surplus) is as large as it can be.',
            'A tax drives a wedge between what buyers pay and sellers receive, reducing the quantity traded. The surplus lost on trades that no longer happen is the deadweight loss.',
          ],
          cards: [fc('Consumer surplus?', 'Willingness to pay minus the price paid.'), fc('Where is total surplus maximised?', 'At the competitive market equilibrium.'), fc('Deadweight loss?', 'The surplus lost on trades that no longer occur because of a tax or other distortion.')],
          questions: [
            q('A buyer is willing to pay 50 and pays 35. Their consumer surplus is:', '15', ['35', '50', '85'], '50 − 35 = 15.'),
            q('Total surplus is greatest:', 'At the market equilibrium quantity', ['Below the equilibrium quantity', 'Above the equilibrium quantity', 'At the maximum price'], 'Every trade worth making occurs and none that is not.'),
            q('What is deadweight loss?', 'Surplus lost on trades that do not happen because of a distortion', ['Tax revenue collected', 'Producer profit', 'Consumer income'], 'Neither buyers, sellers, nor the government captures it.'),
            q('Producer surplus is:', 'Price received minus the cost of production', ['Price paid minus willingness to pay', 'Total revenue', 'Total cost'], 'It measures the gain of sellers from trade.'),
          ],
          remediation: {
            explanation: 'Surplus is the "feel-good" gain from a deal. You were ready to pay 50 and only paid 35: you gained 15. Sellers gain the same way. Deadweight loss is deals that would have made both sides better off but were killed by a tax.',
            steps: ['Pick a demand curve and shade consumer surplus at a price of your choice.', 'Add a tax and shade the deadweight loss triangle.', 'Explain in one sentence why total surplus falls with a tax.'],
          },
        }),
      ],
    },
  ],
}
