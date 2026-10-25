# Error analysis examples (test split, chosen with a fixed random seed)

## BM25 finds it, dense model does not

**Query 3185** (ranks: BM25 1, Dense 129, Hybrid 5)

> ...occasion occurred during the course of the offense or resulted in a conviction for the conduct that occurred on that occasion.” USSG § 2S1.3, comment,  n.3 . According to Peterson, if the structured money came from one source, here her safe deposit box, there could be only one offense, see United States v. Davenport, 929 F.2d 1169, 1172  7th Cir.1991

- Correct holding: holding that the structuring itself and not each individual deposit is the unit of prosecution in a structuring offense
- BM25 top 1: holding that the structuring itself and not each individual deposit is the unit of prosecution in a structuring offense
- Dense top 1: holding that under habitual felony offender statute a sentence includes the sanction of probation

**Query 3045** (ranks: BM25 1, Dense 50, Hybrid 2)

> ...basis and purpose of its actions. See Reytblatt v. United States Nuclear Regulatory Comm’n, 105 F.3d 715, 722-23  D.C.Cir. 1997   “Although the NRC did not directly respond to Dr. Reytblatt’s suggested alternatives ..., its explanation was adequate in light of the general nature of Dr. Reyt-blatt’s comments.... ” ; National Recycling Coalition, Inc. v. Browner, 984 F.2d 1243, 1252  D.C.Cir.1993

- Correct holding: holding that the epas explanation in five different documents of its interpretation of a specific statutory provision satisfied the apas basisandpurpose requirement
- BM25 top 1: holding that the epas explanation in five different documents of its interpretation of a specific statutory provision satisfied the apas basisandpurpose requirement
- Dense top 1: holding that because colorados hazardous waste program was authorized by rcra it became effective pursuant to rcra and the citizen suit provision of section 6972a1a applies

## Dense model finds it, BM25 does not

**Query 2794** (ranks: BM25 102, Dense 1, Hybrid 11)

> ...U.S. 411, 424-25, 96 S.Ct. 820, 828, 46 L.Ed.2d 598  1976 ; and, more important, no newcomer to the jurisprudence of Miranda " . However, in Hall the defendant, a repeat offender, was at least read his rights and the only question was whether he understood them. See also Los Angeles Police Protective League v. Gates, 579 F.Supp 36, 42  C.D.CaI.1984

- Correct holding: holding that although miranda warnings were not given to defendant police officers they had no cause of action under 42 usc  1983 because they were never prosecuted
- BM25 top 1: holding that officers request for defendants name during an illegal entry constituted exploitation of the illegal entry under hall
- Dense top 1: holding that although miranda warnings were not given to defendant police officers they had no cause of action under 42 usc  1983 because they were never prosecuted

**Query 296** (ranks: BM25 1694, Dense 1, Hybrid 69)

> ...2594-95. Obergefell does not create “rights” based on relationships that mock marriage, and no court has so held. The district court’s judgment is AFFIRMED. 1 . The alleged fact dispute does not exist, nor would it be material if it did. While Coker and Golden maintain they were ordered to "cease all contact” with the other  10th Cir. 2008

- Correct holding: holding that governmental actions restricting police officers sexual conduct of an extramarital affair were reasonable
- BM25 top 1: holding nonmoving partys affidavit created genuine issue of material fact as to the existence of an employment relationship
- Dense top 1: holding that governmental actions restricting police officers sexual conduct of an extramarital affair were reasonable

## Hybrid fixes both

**Query 769** (ranks: BM25 2, Dense 4, Hybrid 1)

> ...into a contract for insurance with Allstate. 15 . See also fn. 14, supra. fore not subject to the holding of Mead v. Burns, 199 Conn. 651, 663, 509 A.2d 11  1986 , that CUTPA provides a private right of action for violations of CUIPA. But see Rivera v. Pereira, No. CV010382813S, 2002 WL 377517, *3  Conn.Super. Jan. 25, 2002

- Correct holding: holding that cutpa provides private cause of action for violation of  83a832
- BM25 top 1: holding that connecticuts threeyear limitations period for tort suits set forth in conn genstat  52577 is the appropriate limitations period for civil rights actions under  1983
- Dense top 1: holding that motion to adjudicate lien was not preempted by erisa and illinois common fund doctrine overrode plan language and would reduce plans reimbursement of expenses paid for insured

**Query 3445** (ranks: BM25 2, Dense 10, Hybrid 1)

> ...the agreement, the surrounding circumstances, or both. Id. In this case, Parrish was only one of many health care providers from which Progressive’s insureds could have chosen for treatment of injuries resulting from automobile accidents covered by that policy. See Kelly Health Care, Inc. v. Prudential Ins. Co. of America, Inc., 226 Va. 376, 309 S.E.2d 305, 307  1983

- Correct holding: holding that member of a large class of health care providers available to the insured was only a potential and incidental beneficiary of the contract and thus not entitled to recover thereunder
- BM25 top 1: holding that an agreement in which one party promised to make monthly payments to the other partys attorney as part of an asset sale contract was for the direct benefit of the attorney
- Dense top 1: holding that if an insurer intended to exclude insured contracts from the provision denying coverage for injuries to employees it could have expressly stated as such

## Everything fails

**Query 261** (ranks: BM25 17, Dense 1618, Hybrid 28)

> ...leaving a firm must be allowed, and that it is appropriate for lawyers in these circumstances to make arrangements, prior to their departure, to obtain new office space, equipment, and other materials necessary for the practice of law. Bray v. Squires, 702 S.W.2d 266  Tex. Ct. App. 1985 ; see also Restatement  Second  of Agency § 393, Comment e  1958

- Correct holding: recognizing that agent may make certain preparations for own venture prior to termination of agency
- BM25 top 1: holding that law firm who was plaintiffs adversary in foreclosure proceeding owed no duty to plaintiffs as law firm could not have expected that plaintiffs would rely on law firms representations about payoff amounts
- Dense top 1: holding that a breach of duties that a fiduciary contractually assumes beyond those duties imposed by law is considered to arise out of contract

**Query 2885** (ranks: BM25 3475, Dense 6823, Hybrid inf)

> ...we also held that there was ample reason to believe that the defendant would be carrying drugs, that the second “strip search” took place at a “discreet” location, and that exigent circumstances  consisting of the defendant’s familiarity with processing procedures at the jail and his repeated requests not to be taken there  justified a strip .2d 30, 37  1989

- Correct holding: holding that a panel of the court of appeals is bound by a prior decision of another panel of the same court addressing the same question but in a different case unless overturned by an intervening decision from a higher court
- BM25 top 1: holding that acquiescence to a strip and body cavity search did not extend the scope of defendants consent to search his person because of the highly intrusive nature of the search
- Dense top 1: holding that it was clearly established that a strip search policy applied to minor offense detainees without particularized reasonable suspicion was unlawful
