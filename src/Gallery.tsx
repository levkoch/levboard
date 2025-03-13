import React, { Component, MouseEvent } from "react";
import { ReactComponent as Lemon } from "./image/lemon.svg";


type EntryProps = {
    year: bigint;
    title: string;
    assets: Array<string>;
}

type EntryState = {
    selected: bigint;
}

type GalleryProps = {
  count: bigint;
  assets: Array<GalleryEntry>;
};

type GalleryState = {
  elements?: Array<JSX.Element>;
  selected?: bigint;
};

export class Gallery extends Component<GalleryProps, GalleryState> {
  constructor(props: GalleryProps) {
    super(props);

    this.state = {};
  }

  componentDidMount = () => {
    this.generateEntries();
  };

  render = (): JSX.Element => {
    if (this.state.width === undefined) {
      return <div>Loading galleries...</div>;
    }
    return (
      <div className="infographic">
        <div className="info-title">
          <Lemon className="lemon"/>
          <text className="heading">ALL-TIME ALBUMS</text>
          <span className="years">{this.state.years}</span>
        </div>


      </div>
    );
  };

  onYearClick: (
    year: string,
    offset: bigint
  ) => (_evt: MouseEvent<HTMLButtonElement>) => void = (year, offset) => {
    return (_evt) => {
      console.log(`${year} ${offset}`);

      const scroller = document.getElementById("scroller");
      if (scroller === null) {
        throw new Error("shouldnt happen");
      }
      scroller.scrollLeft = Number(offset) * 3;
    };
  };

  generateEntries = (): void => {
  };
}


class GalleryEntry extends Component<EntryProps, EntryState> {

}
