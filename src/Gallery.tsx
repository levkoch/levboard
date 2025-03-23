import React, { Component, MouseEvent } from "react";
import { ReactComponent as Lemon } from "./image/lemon.svg";

type EntryProps = {
  year: bigint;
  title: string;
  assets: Array<string>;
  description: string;
};

type EntryState = {
  selected: bigint;
};

type GalleryProps = {
  count: bigint;
  metadata: Map<string, EntryProps>;
};

type GalleryState = {
  entries?: Array<GalleryEntry>;
  showing: bigint;
};

export class Gallery extends Component<GalleryProps, GalleryState> {
  constructor(props: GalleryProps) {
    super(props);
    console.log(props);

    this.state = { showing: 2n };
  }

  componentDidMount = () => {
    this.generateEntries();
  };

  render = (): JSX.Element => {
    if (this.state.entries === undefined) {
      return <div>Loading galleries...</div>;
    }

    const assets: Array<JSX.Element> = [];
    this.state.entries.forEach((entry) => {
      assets.push(entry.render());
    });

    return <div className="gallery" children={assets}></div>;
  };

  onMoreClick = (_evt: MouseEvent<HTMLButtonElement>) => {
    if (this.state.showing < this.props.count) {
      var showing = this.state.showing + 2n;
      if (showing > this.props.count) {
        this.setState({ showing: this.props.count });
      } else {
        this.setState({ showing: showing });
      }
    }
  };

  generateEntries = (): void => {
    const entries: Array<GalleryEntry> = [];
    var i = 0n;
    while (i < this.props.count) {
      const metadata: EntryProps | undefined = this.props.metadata.get(
        String(i)
      );
      if (metadata === undefined) {
        throw Error("gallery length was wrong, shouldn't happen");
      }
      entries.push(new GalleryEntry(metadata));
      i += 1n;
    }

    this.setState({ entries: entries });
  };
}

class GalleryEntry extends Component<EntryProps, EntryState> {
  constructor(props: EntryProps) {
    super(props);

    this.state = { selected: 0n };
  }

  render = () => {
    /* <!-- not the biggest fan of whatever the title is trying to be --> */
    return (
      <div className="gallery-entry">
        <div className="info-title">
          <Lemon className="lemon" />
          <span className="heading">{this.props.title}</span>
          <span className="years">{String(this.props.year)}</span>
        </div>

        <img
          className="gallery-image"
          src={"levboard/gallery/" + this.props.assets[0]}
        />
      </div>
    );
  };
}
